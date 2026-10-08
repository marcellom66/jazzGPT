"""Microtiming e velocity applicati dopo la composizione."""

from bisect import bisect_right
from collections import defaultdict
from dataclasses import replace
from math import floor, isfinite, pi, sin
from random import Random

from jazzgpt.events import Performance


class PhraseDynamics:
    """Tocco pianistico sugli attacchi; conserva note, tempi e metadati."""

    def __init__(self, seed: int = 42):
        self.seed = seed

    def apply(self, performance: Performance, *, bars: int) -> Performance:
        if not isinstance(bars, int) or bars < 1:
            raise ValueError("Il numero di battute deve essere positivo")
        if not performance.notes:
            return replace(performance, notes=[])
        beat_seconds = 60 / performance.bpm
        total_beats = bars * 4
        rng = Random(self.seed)
        # Ogni frase ha un punto di massimo diverso: niente onda identica
        # applicata a tutte le battute e niente RNG condiviso con la composizione.
        phrase_shapes = [(rng.uniform(0.35, 0.7), rng.uniform(-2, 2)) for _ in range(bars)]
        melody = sorted((n for n in performance.notes if n.channel == 0), key=lambda n: n.start)
        melody_starts = [n.start for n in melody]
        melody_ends = []
        by_bar = defaultdict(list)
        for note in melody:
            melody_ends.append(max(note.end, melody_ends[-1] if melody_ends else 0))
            bar = min(bars - 1, int(round(note.start / (4 * beat_seconds), 9)))
            by_bar[bar].append(note)
        # Raggruppa gli attacchi entro 20 ms dal primo: il microtiming
        # del generatore può separare un accordo di 18 ms.
        chord_ranks = {}
        comp = sorted((n for n in performance.notes if n.channel == 2), key=lambda n: n.start)
        index = 0
        while index < len(comp):
            end = index + 1
            while end < len(comp) and comp[end].start - comp[index].start <= 0.02:
                end += 1
            pitches = sorted({n.pitch for n in comp[index:end]})
            for note in comp[index:end]:
                chord_ranks[id(note)] = pitches.index(note.pitch) / max(1, len(pitches) - 1)
            index = end
        phrase_details = {}
        for bar, phrase in by_bar.items():
            apex, gain = phrase_shapes[bar]
            previous = phrase[0].pitch
            for index, note in enumerate(phrase):
                position = index / max(1, len(phrase) - 1)
                envelope = position / apex if position <= apex else (1 - position) / (1 - apex)
                accent = 5 if note.end - note.start >= 0.75 * beat_seconds else 0
                accent += 4 if abs(note.pitch - previous) >= 4 else 0
                phrase_details[id(note)] = 9 * envelope + gain + accent
                previous = note.pitch
        notes = []
        for note in performance.notes:
            beat = max(0.0, min(total_beats, note.start / beat_seconds))
            progress = beat / total_beats
            group_start = int(beat // 16) * 16
            group_length = min(16, total_beats - group_start)
            group_phase = (beat - group_start) / group_length if group_length else 1.0
            energy = 18 * sin(pi * progress) + 10 * sin(pi * group_phase)
            release = 10 * max(0.0, (progress - 0.85) / 0.15)
            index = bisect_right(melody_starts, note.start + 0.02) - 1
            active = index >= 0 and melody_ends[index] > note.start
            if note.channel == 0:
                velocity = 52 + energy + phrase_details[id(note)] - release
                # Piccolo residuo del tocco iniziale, senza sostituire il profilo.
                velocity += (note.velocity - 75) * 0.15
            elif note.channel == 1:
                velocity = 42 + 0.45 * energy - 0.4 * release + (-3 if active else 4)
            elif note.channel == 2:
                rank = chord_ranks[id(note)]
                velocity = 31 + 0.3 * energy - 0.3 * release + (-2 if active else 5)
                velocity += -2 + 6 * rank
            else:
                velocity = note.velocity
            notes.append(replace(note, velocity=max(1, min(127, round(velocity)))))
        return replace(performance, notes=notes)


class Humanizer:
    def __init__(self, seed: int = 42, timing_ms: float = 9.0, velocity_spread: int = 5):
        if timing_ms < 0 or velocity_spread < 0:
            raise ValueError("Le variazioni devono essere non negative")
        self.seed, self.timing_ms, self.velocity_spread = seed, timing_ms, velocity_spread

    def apply(
        self, performance: Performance, duration: float, *, bar_duration: float | None = None
    ) -> Performance:
        if bar_duration is not None and (not isfinite(bar_duration) or bar_duration <= 0):
            raise ValueError("La durata della battuta deve essere positiva e finita")
        rng = Random(self.seed)
        notes = []
        # Non introdurre sovrapposizioni della stessa altezza sullo stesso canale.
        last_end: dict[tuple[int, int], float] = {}
        for note in sorted(performance.notes, key=lambda n: (n.start, n.channel, n.pitch)):
            shift = rng.uniform(-self.timing_ms, self.timing_ms) / 1000
            lower, upper = 0.0, duration
            if bar_duration is not None:
                lower = floor(round(note.start / bar_duration, 10)) * bar_duration
                upper = min(duration, lower + bar_duration)
            start = max(lower, note.start + shift, last_end.get((note.channel, note.pitch), 0.0))
            end = min(upper, max(start + 0.001, note.end + shift))
            if end <= start:
                continue
            velocity = min(
                127,
                max(1, note.velocity + rng.randint(-self.velocity_spread, self.velocity_spread)),
            )
            notes.append(replace(note, start=start, end=end, velocity=velocity))
            last_end[(note.channel, note.pitch)] = end
        return replace(performance, notes=notes)
