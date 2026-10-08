"""Trio: silenzi reali, risposte collegate e suoni General MIDI distinti."""

import importlib
import importlib.util
import subprocess
import sys

import mido
import pytest

from jazzgpt.director import GenerationConfig
from jazzgpt.events import Note, Performance
from jazzgpt.harmony import HarmonyEngine
from jazzgpt.midi_io import read_midi, write_midi


def dialogue(config):
    assert importlib.util.find_spec("jazzgpt.ensemble"), "Manca il dialogo tra strumenti"
    return importlib.import_module("jazzgpt.ensemble").generate_dialogue(config)


def test_trio_takes_turns_then_rejoins_without_crossing_turn_boundaries():
    config = GenerationConfig(bars=8)
    performance = dialogue(config)
    for start, channels in [(0, {0, 2}), (4, {1}), (8, {9}), (12, {0, 1, 2, 9})]:
        notes = [n for n in performance.notes if start <= n.start < start + 4]
        assert {n.channel for n in notes} == channels
        assert all(n.end <= start + 4 for n in notes)
    assert performance == dialogue(config)
    assert 15 < performance.duration <= 16


def test_bass_answer_reuses_call_rhythm_and_follows_current_mode():
    performance = dialogue(GenerationConfig(bars=8, humanize=False))
    call = [n for n in performance.notes if n.channel == 0 and n.start < 4]
    answer = [n for n in performance.notes if n.channel == 1 and 4 <= n.start < 8]
    assert [round(n.start, 6) for n in call] == [round(n.start - 4, 6) for n in answer]
    for note in answer:
        assert 36 <= note.pitch <= 59
        assert note.pitch % 12 in HarmonyEngine("C").chord_at(int(note.start / 2)).scale


def test_midi_assigns_acoustic_bass_and_drum_kit(tmp_path):
    source = Performance(
        [Note(72, 0, 0.5), Note(38, 0, 0.5, channel=1), Note(38, 0, 0.1, channel=9)]
    )
    path = write_midi(source, tmp_path / "trio.mid", programs={0: 0, 1: 32, 9: 0})
    programs = {m.channel: m.program for m in mido.MidiFile(path) if m.type == "program_change"}
    assert programs == {0: 0, 1: 32, 9: 0}
    assert len(read_midi(path).notes) == 3


def test_dialogue_requires_complete_eight_bar_cycles():
    with pytest.raises(ValueError):
        dialogue(GenerationConfig(bars=7))


def test_cli_exports_dialogue_with_instrument_assignments(tmp_path):
    output = tmp_path / "dialogue.mid"
    result = subprocess.run(
        [sys.executable, "-m", "jazzgpt", "dialogue", "--bars", "8", "--output", str(output)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "piano" in result.stdout and "basso" in result.stdout and "batteria" in result.stdout
    programs = {m.channel: m.program for m in mido.MidiFile(output) if m.type == "program_change"}
    assert programs[1] == 32 and programs[9] == 0


@pytest.mark.parametrize("bpm,swing,seed", [(31, 0.64, 3), (120, 0.64, 6), (120, 0.75, 3)])
def test_drum_reply_and_fill_do_not_overlap_the_same_drum(bpm, swing, seed):
    performance = dialogue(GenerationConfig(bars=8, bpm=bpm, swing=swing, seed=seed))
    last_end = {}
    for note in sorted(performance.notes, key=lambda n: n.start):
        if note.channel == 9:
            assert note.start >= last_end.get(note.pitch, 0)
            last_end[note.pitch] = note.end
