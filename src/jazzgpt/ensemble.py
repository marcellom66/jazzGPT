"""Dialogo composto tra piano, contrabbasso e batteria General MIDI."""

from collections import defaultdict
from dataclasses import replace
from random import Random

from jazzgpt.director import GenerationConfig, generate
from jazzgpt.events import Note, Performance
from jazzgpt.harmony import HarmonyEngine

TRIO_PROGRAMS = {0: 0, 1: 32, 2: 0, 9: 0}  # Programmi MIDI numerati da zero.
TURN_NAMES = ("piano", "basso", "batteria", "insieme")


def generate_dialogue(config: GenerationConfig) -> Performance:
    """Turni di due battute, in cicli completi di otto battute.

    Basso e batteria riprendono il ritmo della chiamata pianistica del ciclo.
    Non ascolta un ingresso MIDI: è un arrangiamento deterministico offline.
    """
    if config.bars % 8:
        raise ValueError("Il dialogo richiede un numero di battute multiplo di 8")
    source = generate(config)
    harmony = HarmonyEngine(config.key)
    beat_seconds = 60 / config.bpm
    bar_seconds = 4 * beat_seconds
    rng = Random(config.seed + 77)
    by_bar = defaultdict(list)
    for note in source.notes:
        by_bar[int(round(note.start / bar_seconds, 9))].append(note)
    notes = []

    def hit(pitch, beat, velocity):
        notes.append(Note(pitch, beat * beat_seconds, (beat + 0.12) * beat_seconds, velocity, 9))

    for bar in range(config.bars):
        turn = (bar % 8) // 2
        if turn == 0:
            notes.extend(n for n in by_bar[bar] if n.channel in (0, 2))
        elif turn == 1:
            call_bar = bar - 2
            offset = 2 * bar_seconds
            scale = harmony.chord_at(bar).scale
            candidates = [p for p in range(36, 60) if p % 12 in scale]
            for call in sorted(by_bar[call_bar], key=lambda n: n.start):
                if call.channel == 0:
                    target = call.pitch - 24
                    pitch = min(candidates, key=lambda p: abs(p - target))
                    notes.append(
                        replace(
                            call,
                            pitch=pitch,
                            channel=1,
                            start=call.start + offset,
                            end=call.end + offset,
                            velocity=min(105, max(48, call.velocity + 5)),
                        )
                    )
        elif turn == 2:
            call_bar = bar - 4
            offset = 4 * bar_seconds
            call = sorted((n for n in by_bar[call_bar] if n.channel == 0), key=lambda n: n.start)
            hit(36, bar * 4, rng.randint(55, 67))
            for index, note in enumerate(call):
                # Il rullante riprende gli accenti, il charleston le risposte leggere.
                pitch = 38 if index % 2 == 0 else 42
                beat = (note.start + offset) / beat_seconds
                hit(pitch, beat, min(100, max(45, note.velocity - 5)))
            if bar % 2:
                # Quattro tom distinti: il fill non riattacca un rullante
                # eventualmente ancora attivo nella risposta al motivo.
                for index, pitch in enumerate((45, 47, 50, 48)):
                    hit(pitch, bar * 4 + 3 + index * 0.25, 60 + index * 5)
        else:
            notes.extend(by_bar[bar])
            swing = config.swing if config.style == "swing" else 0.5
            for beat in range(4):
                hit(51, bar * 4 + beat, rng.randint(36, 47))  # Ride leggero.
                if beat % 2:
                    hit(44, bar * 4 + beat, rng.randint(31, 40))
                    hit(51, bar * 4 + beat + swing, rng.randint(29, 39))
                else:
                    hit(36, bar * 4 + beat, rng.randint(32, 43))
    return Performance(
        sorted(notes, key=lambda n: (n.start, n.channel, n.pitch)),
        bpm=config.bpm,
        title=f"JazzGPT trio: domanda e risposta ({config.style})",
    )
