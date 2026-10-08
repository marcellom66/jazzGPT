"""Rappresentazione canonica: secondi assoluti, pitch/velocity MIDI."""

from dataclasses import dataclass, field
from math import isfinite


@dataclass(frozen=True)
class Note:
    pitch: int
    start: float
    end: float
    velocity: int = 80
    channel: int = 0

    def __post_init__(self):
        if not isinstance(self.pitch, int) or not 0 <= self.pitch <= 127:
            raise ValueError("pitch deve essere un intero MIDI 0..127")
        if not isinstance(self.velocity, int) or not 1 <= self.velocity <= 127:
            raise ValueError("velocity deve essere un intero 1..127")
        if not isinstance(self.channel, int) or not 0 <= self.channel <= 15:
            raise ValueError("channel deve essere un intero 0..15")
        if not all(isfinite(v) for v in (self.start, self.end)):
            raise ValueError("I tempi devono essere finiti")
        if self.start < 0 or self.end <= self.start:
            raise ValueError("La nota deve avere inizio >= 0 e durata positiva")


@dataclass(frozen=True)
class Pedal:
    time: float
    value: int
    channel: int = 0

    def __post_init__(self):
        if not isfinite(self.time) or self.time < 0:
            raise ValueError("Tempo del pedale non valido")
        if not isinstance(self.value, int) or not 0 <= self.value <= 127:
            raise ValueError("Valore del pedale non valido")
        if not isinstance(self.channel, int) or not 0 <= self.channel <= 15:
            raise ValueError("Canale del pedale non valido")


@dataclass
class Performance:
    notes: list[Note] = field(default_factory=list)
    pedals: list[Pedal] = field(default_factory=list)
    bpm: float = 120.0
    title: str = "JazzGPT"

    def __post_init__(self):
        if not isfinite(self.bpm) or not 4 <= self.bpm <= 1000:
            raise ValueError("bpm deve essere finito e compreso tra 4 e 1000")

    @property
    def duration(self) -> float:
        return max([0.0] + [n.end for n in self.notes] + [p.time for p in self.pedals])
