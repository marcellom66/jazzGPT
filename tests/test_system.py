"""Contratti osservabili: MIDI valido, tempi, armonia, memoria e CLI."""

import importlib.util
import json
import subprocess
import sys

import mido
import pytest


def test_package_exists():
    assert importlib.util.find_spec("jazzgpt") is not None
    import jazzgpt

    assert getattr(jazzgpt, "__version__", None) == "0.1.0"


def test_tokenizer_roundtrip_preserves_polyphony_channels_and_pedal():
    from jazzgpt.events import Note, Pedal, Performance
    from jazzgpt.tokenizer import EventTokenizer

    original = Performance(
        notes=[Note(60, 0.0, 0.501, 77), Note(64, 0.237, 0.801, 62), Note(60, 0.02, 0.22, 55, 1)],
        pedals=[Pedal(0.03, 127), Pedal(0.9, 0)],
    )
    tokenizer = EventTokenizer()
    tokens = tokenizer.encode(original)
    restored = tokenizer.decode(tokens)
    assert sorted(restored.notes, key=lambda n: (n.start, n.pitch)) == sorted(
        original.notes, key=lambda n: (n.start, n.pitch)
    )
    assert restored.pedals == original.pedals
    assert max(tokens) < tokenizer.vocab_size


def test_tokenizer_splits_long_silence_and_rejects_dangling_notes():
    from jazzgpt.events import Note, Performance
    from jazzgpt.tokenizer import EventTokenizer

    tok = EventTokenizer()
    result = tok.decode(tok.encode(Performance([Note(72, 10.0, 10.2, 90)])))
    assert result.notes[0].start == 10.0
    with pytest.raises(ValueError, match="incomplete"):
        tok.decode([tok.token_id("BOS"), tok.token_id("NOTE_ON_60"), tok.token_id("EOS")])


@pytest.mark.parametrize(
    "kwargs",
    [{"pitch": 128}, {"velocity": 0}, {"end": 0}, {"channel": 16}, {"start": float("nan")}],
)
def test_invalid_notes_are_rejected(kwargs):
    from jazzgpt.events import Note

    params = dict(pitch=60, start=0.0, end=0.5, velocity=80)
    params.update(kwargs)
    with pytest.raises(ValueError):
        Note(**params)


def test_harmony_transposes_and_rejects_unknown_keys():
    from jazzgpt.harmony import HarmonyEngine

    harmony = HarmonyEngine("C")
    assert [harmony.chord_at(i).symbol for i in range(4)] == ["Dm7", "G7", "Cmaj7", "A7"]
    assert HarmonyEngine("F").chord_at(0).root == 7
    assert 2 in harmony.chord_at(0).pitch_classes
    with pytest.raises(ValueError, match="tonalità"):
        HarmonyEngine("H")


def test_memory_is_bounded_and_motif_recall_is_relative():
    from jazzgpt.memory import PhraseMemory

    memory = PhraseMemory(capacity=2)
    for pitches in ([60, 62, 65], [67, 69, 72], [64, 65, 67]):
        memory.remember(pitches)
    assert len(memory.motifs) == 2
    assert memory.recall(70, 0) == [70, 72, 75]


def test_generation_is_reproducible_polyphonic_and_bounded():
    from jazzgpt.director import GenerationConfig, generate

    config = GenerationConfig(bars=8, bpm=120, seed=7)
    first, second = generate(config), generate(config)
    assert first == second
    assert len(first.notes) > 60
    assert {n.channel for n in first.notes} == {0, 1, 2}
    assert min(n.start for n in first.notes) >= 0
    assert max(n.end for n in first.notes) <= 16.0
    assert generate(GenerationConfig(bars=8, bpm=120, seed=8)) != first


@pytest.mark.parametrize(
    "kwargs", [{"bars": 0}, {"bpm": 0}, {"bpm": float("nan")}, {"swing": 0.9}, {"bars": 10001}]
)
def test_bad_generation_config(kwargs):
    from jazzgpt.director import GenerationConfig

    with pytest.raises(ValueError):
        GenerationConfig(**kwargs)


def test_humanizer_keeps_notes_inside_piece():
    from jazzgpt.events import Note, Performance
    from jazzgpt.performer import Humanizer

    result = Humanizer(seed=1).apply(Performance([Note(60, 0, 0.5, 127)]), 0.5)
    assert 0 <= result.notes[0].start < result.notes[0].end <= 0.5
    assert 1 <= result.notes[0].velocity <= 127


def test_midi_roundtrip_and_no_stuck_notes(tmp_path):
    from jazzgpt.director import GenerationConfig, generate
    from jazzgpt.midi_io import read_midi, write_midi

    performance = generate(GenerationConfig(bars=4, bpm=110, seed=5))
    path = tmp_path / "test.mid"
    write_midi(performance, path)
    restored = read_midi(path)
    assert len(restored.notes) == len(performance.notes)
    assert restored.bpm == pytest.approx(110, abs=0.01)
    assert restored.duration == pytest.approx(performance.duration, abs=0.002)
    active = {}
    for message in mido.MidiFile(path):
        if message.type == "note_on" and message.velocity > 0:
            key = (message.channel, message.note)
            active[key] = active.get(key, 0) + 1
        elif message.type == "note_off":
            key = (message.channel, message.note)
            active[key] = active.get(key, 0) - 1
            assert active[key] >= 0
    assert all(count == 0 for count in active.values())


def test_midi_reader_uses_tempo_changes(tmp_path):
    from jazzgpt.midi_io import read_midi

    midi = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    midi.tracks.append(track)
    track.extend(
        [
            mido.MetaMessage("set_tempo", tempo=500000),
            mido.Message("note_on", note=60, velocity=80),
            mido.MetaMessage("set_tempo", tempo=1000000, time=480),
            mido.Message("note_off", note=60, time=480),
        ]
    )
    path = tmp_path / "tempo.mid"
    midi.save(path)
    assert read_midi(path).notes[0].end == 1.5


def test_cli_generates_midi_and_json_without_torch(tmp_path):
    output = tmp_path / "demo.mid"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "jazzgpt",
            "generate",
            "--bars",
            "4",
            "--output",
            str(output),
            "--tokens",
            str(tmp_path / "tokens.json"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert len(mido.MidiFile(output).tracks) > 0
    payload = json.loads((tmp_path / "tokens.json").read_text())
    assert payload["format"] == "jazzgpt-events-v1"
    assert len(payload["tokens"]) > 10
    assert "torch" not in sys.modules


def test_aria_placeholder_has_explicit_error():
    from jazzgpt.models.aria import AriaAdapter

    with pytest.raises(NotImplementedError, match="tokenizer"):
        AriaAdapter().generate(None)


@pytest.mark.parametrize("times", [(0.1001, 0.1002), (0.1, 0.1)])
def test_pedal_order_survives_millisecond_rounding(times):
    from jazzgpt.events import Pedal, Performance
    from jazzgpt.tokenizer import EventTokenizer

    tokenizer = EventTokenizer()
    original = Performance(pedals=[Pedal(times[0], 127), Pedal(times[1], 0)])
    restored = tokenizer.decode(tokenizer.encode(original))
    assert [p.value for p in restored.pedals] == [127, 0]


def test_initial_bpm_is_default_when_first_tempo_change_is_later(tmp_path):
    from jazzgpt.midi_io import read_midi

    midi = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    midi.tracks.append(track)
    track.extend(
        [
            mido.Message("note_on", note=60, velocity=80),
            mido.MetaMessage("set_tempo", tempo=1000000, time=480),
            mido.Message("note_off", note=60, time=480),
        ]
    )
    path = tmp_path / "late-tempo.mid"
    midi.save(path)
    performance = read_midi(path)
    assert performance.bpm == 120
    assert performance.notes[0].end == 1.5
