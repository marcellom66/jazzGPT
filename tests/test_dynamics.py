"""Dinamiche strutturate: intensità, equilibrio e conservazione del brano."""

from dataclasses import replace

from jazzgpt import performer
from jazzgpt.events import Note, Performance


def dynamic_performer():
    assert hasattr(performer, "PhraseDynamics"), "Manca il trattamento dinamico delle frasi"
    return performer.PhraseDynamics(seed=42)


def test_dynamics_preserve_pitches_timing_channels_and_metadata():
    source = Performance(
        [
            Note(72, 0, 0.4, 80),
            Note(76, 0.5, 1.1, 80),
            Note(74, 1.5, 1.9, 80),
            Note(38, 0, 1, 60, 1),
            Note(53, 0, 0.7, 50, 2),
        ],
        bpm=120,
        title="Confronto",
    )
    result = dynamic_performer().apply(source, bars=1)
    assert [replace(n, velocity=80) for n in result.notes] == [
        replace(n, velocity=80) for n in source.notes
    ]
    assert result.bpm == source.bpm and result.title == source.title
    assert result.pedals == source.pedals
    assert result == dynamic_performer().apply(source, bars=1)
    assert [n.velocity for n in source.notes] == [80, 80, 80, 60, 50]


def test_long_form_grows_then_releases_instead_of_staying_flat():
    source = Performance([Note(72, i * 0.25, i * 0.25 + 0.2, 80) for i in range(64)])
    result = dynamic_performer().apply(source, bars=8)
    velocities = [n.velocity for n in result.notes]
    beginning = sum(velocities[:8]) / 8
    middle = sum(velocities[24:40]) / 16
    ending = sum(velocities[-8:]) / 8
    assert middle >= beginning + 8
    assert middle >= ending + 8
    assert max(velocities) - min(velocities) >= 20


def test_accompaniment_yields_to_melody_and_voices_chord_top_note():
    source = Performance(
        [
            Note(76, 0, 0.9, 80),
            Note(38, 0, 0.5, 60, 1),
            Note(38, 1, 1.5, 60, 1),
            Note(53, 0, 0.5, 50, 2),
            Note(57, 0, 0.5, 50, 2),
            Note(60, 0, 0.5, 50, 2),
            Note(53, 1, 1.5, 50, 2),
            Note(57, 1, 1.5, 50, 2),
            Note(60, 1, 1.5, 50, 2),
        ]
    )
    notes = dynamic_performer().apply(source, bars=1).notes
    assert notes[0].velocity > notes[1].velocity > notes[3].velocity
    assert notes[2].velocity > notes[1].velocity
    assert notes[6].velocity > notes[3].velocity
    assert notes[5].velocity > notes[4].velocity > notes[3].velocity


def test_dynamics_support_empty_performance_and_midi_velocity_limits():
    dynamics = dynamic_performer()
    assert dynamics.apply(Performance(), bars=1).notes == []
    source = Performance([Note(127, 0, 0.5, 127), Note(0, 0, 0.5, 1, 2)])
    assert all(1 <= n.velocity <= 127 for n in dynamics.apply(source, bars=1).notes)


def test_chord_voicing_survives_microtiming_across_rounding_boundary():
    source = Performance(
        [
            Note(76, 0, 0.9, 80),
            Note(53, 0.376, 0.7, 50, 2),
            Note(57, 0.373, 0.7, 50, 2),
            Note(60, 0.374, 0.7, 50, 2),
        ]
    )
    notes = dynamic_performer().apply(source, bars=1).notes
    assert notes[3].velocity > notes[2].velocity > notes[1].velocity
