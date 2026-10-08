"""Memoria di frasi come intervalli relativi, con capacità limitata."""

from collections import deque


class PhraseMemory:
    def __init__(self, capacity: int = 8):
        if capacity < 1:
            raise ValueError("capacity deve essere positiva")
        self.motifs: deque[tuple[int, ...]] = deque(maxlen=capacity)

    def remember(self, pitches: list[int]) -> None:
        if len(pitches) >= 3:
            self.motifs.append(tuple(p - pitches[0] for p in pitches[:8]))

    def recall(self, anchor: int, index: int = -1) -> list[int]:
        if not self.motifs:
            return []
        return [anchor + interval for interval in self.motifs[index]]
