"""Armonia del baseline: un accordo per battuta, ii–V–I–VI7."""

from dataclasses import dataclass

KEYS = {
    "C": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11,
}
NAMES = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")
INTERVALS = {"m7": (0, 3, 7, 10), "7": (0, 4, 7, 10), "maj7": (0, 4, 7, 11)}
SCALES = {"m7": (0, 2, 3, 5, 7, 9, 10), "7": (0, 2, 4, 5, 7, 9, 10), "maj7": (0, 2, 4, 5, 7, 9, 11)}


@dataclass(frozen=True)
class Chord:
    root: int
    quality: str

    @property
    def symbol(self) -> str:
        return NAMES[self.root] + self.quality

    @property
    def pitch_classes(self) -> tuple[int, ...]:
        return tuple((self.root + i) % 12 for i in INTERVALS[self.quality])

    @property
    def scale(self) -> tuple[int, ...]:
        return tuple((self.root + i) % 12 for i in SCALES[self.quality])

    def voicing(self) -> list[int]:
        # Terza, settima e nona: rootless voicing compatto nella mano sinistra.
        third, seventh = INTERVALS[self.quality][1], INTERVALS[self.quality][3]
        pitches = [48 + (self.root + i) % 12 for i in (third, seventh, 2)]
        return sorted(pitches)


class HarmonyEngine:
    def __init__(self, key: str = "C"):
        if key not in KEYS:
            raise ValueError(f"tonalità non supportata: {key}; usa {', '.join(KEYS)}")
        self.key = key
        tonic = KEYS[key]
        self.progression = [
            Chord((tonic + offset) % 12, quality)
            for offset, quality in ((2, "m7"), (7, "7"), (0, "maj7"), (9, "7"))
        ]

    def chord_at(self, bar: int) -> Chord:
        if bar < 0:
            raise ValueError("La battuta deve essere >= 0")
        return self.progression[bar % len(self.progression)]
