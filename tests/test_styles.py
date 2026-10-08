"""Profili di stile e transizioni nella stessa performance MIDI."""

import subprocess
import sys
from dataclasses import replace

import pytest

from jazzgpt import director
from jazzgpt.director import GenerationConfig, generate
from jazzgpt.midi_io import read_midi, write_midi


def style_config(style, **kwargs):
    assert "style" in GenerationConfig.__dataclass_fields__, "Mancano i profili di stile"
    return GenerationConfig(style=style, **kwargs)


def test_ballad_has_longer_melody_notes_and_less_dense_accompaniment():
    swing = generate(style_config("swing", bars=8, humanize=False))
    ballad = generate(style_config("ballad", bars=8, humanize=False))

    def melody(performance):
        return [n for n in performance.notes if n.channel == 0]

    assert len(melody(ballad)) < len(melody(swing))
    assert sum(n.end - n.start for n in melody(ballad)) / len(melody(ballad)) > 0.7
    assert len([n for n in ballad.notes if n.channel == 2]) < len(
        [n for n in swing.notes if n.channel == 2]
    )


def test_latin_uses_straight_subdivisions_and_syncopated_comping():
    config = style_config("latin", bars=8, humanize=False)
    performance = generate(config)
    for note in performance.notes:
        beats = note.start * config.bpm / 60
        assert beats * 2 == pytest.approx(round(beats * 2))
    assert any(
        (n.start * config.bpm / 60) % 1 == pytest.approx(0.5)
        for n in performance.notes
        if n.channel == 2
    )
    assert performance != generate(replace(config, style="swing"))


def test_medley_has_three_sections_with_valid_midi_and_reproducible_seed(tmp_path):
    assert hasattr(director, "generate_medley"), "Manca la demo con più stili"
    config = GenerationConfig(bars=4, bpm=120, seed=42)
    medley = director.generate_medley(config)
    assert medley == director.generate_medley(config)
    assert 23 < medley.duration <= 24
    for start in (0, 8, 16):
        section = [n for n in medley.notes if start <= n.start < start + 8]
        assert {n.channel for n in section} == {0, 1, 2}
        assert all(n.end <= start + 8 for n in section)
    path = write_midi(medley, tmp_path / "medley.mid")
    assert len(read_midi(path).notes) == len(medley.notes)


def test_unknown_style_and_invalid_medley_section_count_are_rejected():
    with pytest.raises(ValueError, match="stile"):
        style_config("unknown")
    assert hasattr(director, "generate_medley")
    with pytest.raises(ValueError):
        director.generate_medley(GenerationConfig(), styles=("swing",))


def test_cli_creates_two_style_demo_and_reports_section_boundaries(tmp_path):
    output = tmp_path / "two_styles.mid"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "jazzgpt",
            "medley",
            "--bars-per-style",
            "4",
            "--styles",
            "ballad",
            "latin",
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "ballad" in result.stdout and "latin" in result.stdout
    assert "8.00" in result.stdout
    assert 15 < read_midi(output).duration <= 16
