"""Vincoli musicali osservabili; la qualità resta una verifica d'ascolto."""

import pytest

from jazzgpt.director import GenerationConfig, generate
from jazzgpt.harmony import HarmonyEngine


@pytest.mark.parametrize("key", ["C", "Eb", "F#"])
@pytest.mark.parametrize("humanize", [False, True])
@pytest.mark.parametrize("bpm", [31, 120, 300])
def test_baseline_notes_stay_in_current_chord_mode(key, humanize, bpm):
    harmony = HarmonyEngine(key)
    for seed in range(6):
        config = GenerationConfig(bars=16, key=key, seed=seed, humanize=humanize, bpm=bpm)
        performance = generate(config)
        for note in performance.notes:
            # Tolleranza solo agli errori floating-point sui confini esatti.
            bar = int(round(note.start / (4 * 60 / config.bpm), 9))
            assert note.pitch % 12 in harmony.chord_at(bar).scale


def test_melody_uses_short_and_long_notes_with_phrase_spaces():
    performance = generate(GenerationConfig(bars=8, humanize=False))
    melody = sorted((n for n in performance.notes if n.channel == 0), key=lambda n: n.start)
    durations = {round(n.end - n.start, 3) for n in melody}
    assert len(durations) >= 4
    assert max(durations) >= 0.6
    assert any(b.start - a.end >= 0.3 for a, b in zip(melody, melody[1:]))


@pytest.mark.parametrize("channel", [1, 2])
def test_accompaniment_changes_rhythm_between_bars(channel):
    config = GenerationConfig(bars=8, bpm=120, humanize=False)
    notes = generate(config).notes
    rhythms = set()
    for bar in range(config.bars):
        rhythms.add(
            tuple(
                sorted(
                    {
                        round(n.start - 2 * bar, 3)
                        for n in notes
                        if n.channel == channel and 2 * bar <= n.start < 2 * (bar + 1)
                    }
                )
            )
        )
    assert len(rhythms) >= 3


def test_melody_avoids_three_identical_pitches_in_a_row():
    for seed in range(6):
        melody = [
            n.pitch
            for n in sorted(
                generate(GenerationConfig(bars=16, seed=seed)).notes, key=lambda n: n.start
            )
            if n.channel == 0
        ]
        assert all(a != b or b != c for a, b, c in zip(melody, melody[1:], melody[2:]))
