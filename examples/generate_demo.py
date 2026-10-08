"""Esempio API: eseguire dalla cartella progetto dopo pip install -e ."""

from pathlib import Path

from jazzgpt.director import GenerationConfig, generate
from jazzgpt.midi_io import write_midi

if __name__ == "__main__":
    performance = generate(GenerationConfig(bars=16, bpm=105, key="F", seed=123))
    path = write_midi(performance, Path("renders/api_demo.mid"))
    print(f"Creato {path}: {len(performance.notes)} note")
