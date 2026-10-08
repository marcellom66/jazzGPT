"""Forma e orchestration: pianoforte solo con tre voci MIDI."""

from dataclasses import dataclass, replace
from math import isfinite, pi, sin
from random import Random

from jazzgpt.events import Note, Performance
from jazzgpt.harmony import HarmonyEngine
from jazzgpt.memory import PhraseMemory
from jazzgpt.models.base import NoteContext, NoteModel
from jazzgpt.models.baseline import RuleBasedModel
from jazzgpt.performer import Humanizer, PhraseDynamics


@dataclass(frozen=True)
class GenerationConfig:
    bars: int = 8
    bpm: float = 120.0
    key: str = "C"
    seed: int = 42
    swing: float = 0.64
    humanize: bool = True
    style: str = "swing"

    def __post_init__(self):
        if not isinstance(self.bars, int) or not 1 <= self.bars <= 10000:
            raise ValueError("bars deve essere un intero tra 1 e 10000")
        if not isfinite(self.bpm) or not 30 <= self.bpm <= 300:
            raise ValueError("bpm deve essere tra 30 e 300")
        if not isfinite(self.swing) or not 0.5 <= self.swing <= 0.75:
            raise ValueError("swing deve essere tra 0.5 e 0.75")
        HarmonyEngine(self.key)
        if self.style not in STYLE_PROFILES:
            raise ValueError(f"stile non supportato: {self.style}")


@dataclass(frozen=True)
class BarPlan:
    bar: int
    tension: float
    density: float
    recall_motif: bool


class Director:
    def plan(self, config: GenerationConfig) -> list[BarPlan]:
        return [
            BarPlan(
                i,
                0.35 + 0.6 * sin(pi * i / max(1, config.bars - 1)),
                0.60 if i % 4 == 3 else 0.85,
                i % 4 == 2,
            )
            for i in range(config.bars)
        ]


# Coppie (inizio, durata) in beat: brevi cellule, note tenute e silenzi.
MELODY_RHYTHMS = (
    ((0.0, 0.5), (0.5, 0.5), (1.0, 1.5), (3.0, 0.5)),
    ((0.5, 0.5), (1.0, 0.5), (1.5, 0.5), (2.0, 1.0), (3.5, 0.5)),
    ((0.0, 1.5), (2.0, 0.5), (2.5, 0.5), (3.0, 1.0)),
    ((0.0, 0.5), (1.0, 0.5), (1.5, 1.0), (3.0, 0.5), (3.5, 0.5)),
    ((0.0, 1.0), (1.5, 0.5), (2.0, 0.5), (2.5, 0.5), (3.0, 1.0)),
    ((0.5, 1.0), (2.0, 1.5)),
)
BASS_RHYTHMS = ((0.0, 2.0), (0.0, 1.5, 3.0), (0.0, 1.0, 2.0, 3.0), (0.0, 2.5, 3.5))
COMP_RHYTHMS = ((0.5, 2.5), (0.0, 1.5, 3.5), (1.0, 3.0), (0.0, 2.0), (0.5, 1.5, 3.0))


@dataclass(frozen=True)
class StyleProfile:
    melody: tuple
    bass: tuple
    comp: tuple
    swung: bool = True
    melody_gate: tuple[float, float] = (0.82, 0.97)
    bass_gate: tuple[float, float] = (0.72, 0.9)
    comp_lengths: tuple[float, ...] = (0.3, 0.65, 1.2)
    root_fifth_bass: bool = False
    dynamic_scale: float = 1.0


# Profili pianistici ispirati agli stili: nessuna pretesa di imitazione completa.
STYLE_PROFILES = {
    "swing": StyleProfile(MELODY_RHYTHMS, BASS_RHYTHMS, COMP_RHYTHMS),
    "ballad": StyleProfile(
        melody=(
            ((0.0, 2.0), (2.5, 1.5)),
            ((0.5, 1.5), (2.5, 1.5)),
            ((0.0, 3.0), (3.5, 0.5)),
            ((0.0, 1.5), (2.0, 2.0)),
            ((0.0, 1.0), (1.5, 1.0), (3.0, 1.0)),
        ),
        bass=((0.0,), (0.0, 2.0), (0.0, 3.0)),
        comp=((0.0,), (0.5,), (0.0, 2.5), (1.0, 3.0)),
        swung=False,
        melody_gate=(0.93, 0.99),
        bass_gate=(0.85, 0.96),
        comp_lengths=(1.2, 2.0, 3.0),
        dynamic_scale=0.86,
    ),
    "latin": StyleProfile(
        melody=(
            ((0.0, 0.5), (0.5, 1.0), (2.0, 0.5), (2.5, 1.0)),
            ((0.5, 0.5), (1.0, 1.0), (2.5, 0.5), (3.0, 1.0)),
            ((0.0, 1.0), (1.5, 0.5), (2.0, 1.0), (3.5, 0.5)),
            ((0.0, 0.5), (1.0, 0.5), (1.5, 0.5), (2.5, 0.5), (3.5, 0.5)),
        ),
        bass=((0.0, 2.0), (0.0, 2.5), (0.0, 1.5, 2.0, 3.5)),
        comp=((0.0, 1.5, 2.5), (0.5, 2.0, 3.5), (0.0, 1.5, 3.0), (0.5, 1.5, 2.5, 3.5)),
        swung=False,
        melody_gate=(0.72, 0.9),
        bass_gate=(0.62, 0.82),
        comp_lengths=(0.25, 0.4, 0.65),
        root_fifth_bass=True,
    ),
}


def _choose_rhythm(patterns, recent: list[int], rng: Random):
    choices = [i for i in range(len(patterns)) if i not in recent[-2:]]
    index = rng.choice(choices)
    recent.append(index)
    del recent[:-2]
    return patterns[index]


def _swing_beat(beat: float, swing: float) -> float:
    whole = int(beat)
    return whole + (swing if beat - whole == 0.5 else beat - whole)


def generate(config: GenerationConfig, model: NoteModel | None = None) -> Performance:
    """Genera note in modo sequenziale; modello sostituibile via dependency injection."""
    rng = Random(config.seed)
    profile = STYLE_PROFILES[config.style]
    swing = config.swing if profile.swung else 0.5
    model = model or RuleBasedModel()
    harmony, memory = HarmonyEngine(config.key), PhraseMemory()
    notes: list[Note] = []
    history: list[int] = []
    recent_melody: list[int] = []
    recent_bass: list[int] = []
    recent_comp: list[int] = []
    seconds_per_beat = 60.0 / config.bpm
    total_duration = config.bars * 4 * seconds_per_beat

    def add(pitch: int, beat: float, length: float, velocity: int, channel: int):
        notes.append(
            Note(
                pitch,
                beat * seconds_per_beat,
                min(total_duration, (beat + length) * seconds_per_beat),
                velocity,
                channel,
            )
        )

    for plan in Director().plan(config):
        chord = harmony.chord_at(plan.bar)
        start = plan.bar * 4
        scale_notes = [p for p in range(60, 85) if p % 12 in chord.scale]
        anchor_pitch = history[-1] if history else 72
        anchor = min(range(len(scale_notes)), key=lambda i: abs(scale_notes[i] - anchor_pitch))
        anchor = max(3, min(len(scale_notes) - 5, anchor + rng.choice((-2, -1, 0, 1))))
        if memory.motifs and plan.bar % 4 != 0:
            # La memoria contiene gradi diatonici, non distanze in semitoni.
            motif = memory.recall(0)
            if plan.bar % 4 == 2:
                motif = [-degree for degree in motif]
            motif = [degree + rng.choice((-1, 0, 1)) for degree in motif]
        else:
            motif = list(rng.choice(((0, 1, 3, 2), (0, -2, -1, 1), (0, 2, 1, -1))))
        rhythm = _choose_rhythm(profile.melody, recent_melody, rng)
        phrase_degrees = []
        for step, (offset, length) in enumerate(rhythm):
            degree = max(0, min(len(scale_notes) - 1, anchor + motif[step % len(motif)]))
            target = scale_notes[degree]
            if step == len(rhythm) - 1:
                # Chiusura sulla terza/settima corrente o su una nota comune
                # all'accordo seguente: la frase ha una destinazione.
                next_chord = harmony.chord_at(plan.bar + 1)
                destinations = [p for p in scale_notes if p % 12 in next_chord.pitch_classes]
                target = min(destinations, key=lambda p: abs(p - target))
            beat = start + _swing_beat(offset, swing)
            context = NoteContext(
                chord,
                tuple(history[-32:]),
                offset % 1 == 0,
                plan.tension,
                target,
            )
            pitch = model.next_pitch(context, rng)
            end = start + _swing_beat(offset + length, swing)
            articulation = rng.uniform(*profile.melody_gate)
            velocity = int(70 + 13 * sin(pi * step / max(1, len(rhythm) - 1)))
            velocity += rng.randint(-5, 5) + (3 if offset % 1 != 0 else 0)
            add(pitch, beat, (end - beat) * articulation, velocity, 0)
            history.append(pitch)
            history = history[-32:]
            # Un NoteModel esterno può usare note fuori dal modo: il contratto
            # resta libero; la memoria le proietta sul grado più vicino.
            phrase_degrees.append(
                min(range(len(scale_notes)), key=lambda i: abs(scale_notes[i] - pitch))
            )
        memory.remember(phrase_degrees)

        bass_rhythm = _choose_rhythm(profile.bass, recent_bass, rng)
        bass_notes = [p for p in range(36, 54) if p % 12 in chord.pitch_classes]
        bass_pitch = 36 + chord.root
        for index, offset in enumerate(bass_rhythm):
            if profile.root_fifth_bass:
                bass_pitch = 36 + chord.root + (7 if index % 2 else 0)
            elif index:
                candidates = [p for p in bass_notes if p != bass_pitch]
                destination = 36 + harmony.chord_at(plan.bar + 1).root
                bass_pitch = (
                    min(candidates, key=lambda p: abs(p - destination))
                    if index == len(bass_rhythm) - 1
                    else rng.choice(candidates)
                )
            next_offset = bass_rhythm[index + 1] if index + 1 < len(bass_rhythm) else 4.0
            beat = _swing_beat(offset, swing)
            length = (_swing_beat(next_offset, swing) - beat) * rng.uniform(*profile.bass_gate)
            add(bass_pitch, start + beat, length, rng.randint(48, 60), 1)

        comp_rhythm = _choose_rhythm(profile.comp, recent_comp, rng)
        voicing = chord.voicing()
        if rng.random() < 0.5:
            voicing = sorted(voicing[1:] + [voicing[0] + 12])
        for index, offset in enumerate(comp_rhythm):
            next_offset = comp_rhythm[index + 1] if index + 1 < len(comp_rhythm) else 4.0
            beat = _swing_beat(offset, swing)
            available = _swing_beat(next_offset, swing) - beat
            length = min(available * 0.85, rng.choice(profile.comp_lengths))
            velocity = rng.randint(39, 52)
            for pitch in voicing:
                add(pitch, start + beat, length, velocity + rng.randint(-3, 3), 2)
    performance = Performance(
        notes,
        bpm=config.bpm,
        title=f"JazzGPT {config.style}: variazioni modali ii–V–I–VI7 in {config.key}",
    )
    performance = (
        Humanizer(config.seed + 1).apply(
            performance, total_duration, bar_duration=4 * seconds_per_beat
        )
        if config.humanize
        else performance
    )
    performance = PhraseDynamics(config.seed + 2).apply(performance, bars=config.bars)
    if profile.dynamic_scale != 1:
        performance = replace(
            performance,
            notes=[
                replace(n, velocity=max(1, round(n.velocity * profile.dynamic_scale)))
                for n in performance.notes
            ],
        )
    return performance


def generate_medley(
    config: GenerationConfig, styles: tuple[str, ...] = ("swing", "ballad", "latin")
) -> Performance:
    """Due o tre sezioni; config.bars indica le battute di ciascuna sezione.

    Il BPM resta costante; la ballad è interpretata in half-time. Le sezioni
    hanno confini esatti anche se la loro ultima nota termina in anticipo.
    """
    if not 2 <= len(styles) <= 3 or any(style not in STYLE_PROFILES for style in styles):
        raise ValueError("Scegli due o tre stili tra swing, ballad e latin")
    notes, pedals = [], []
    section_duration = config.bars * 4 * 60 / config.bpm
    for index, style in enumerate(styles):
        section = generate(replace(config, style=style, seed=config.seed + index * 101))
        offset = index * section_duration
        notes.extend(replace(n, start=n.start + offset, end=n.end + offset) for n in section.notes)
        pedals.extend(replace(p, time=p.time + offset) for p in section.pedals)
    return Performance(notes, pedals, config.bpm, "JazzGPT: " + " / ".join(styles))
