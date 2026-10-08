"""Contratti per modelli a livello di nota e continuazione di performance."""

from dataclasses import dataclass
from random import Random
from typing import Protocol

from jazzgpt.events import Performance
from jazzgpt.harmony import Chord


@dataclass(frozen=True)
class NoteContext:
    chord: Chord
    history: tuple[int, ...]
    strong_beat: bool
    tension: float
    target: int | None = None


class NoteModel(Protocol):
    def next_pitch(self, context: NoteContext, rng: Random) -> int: ...


class ContinuationBackend(Protocol):
    def continue_midi(self, prompt: Performance, max_new_tokens: int) -> Performance: ...
