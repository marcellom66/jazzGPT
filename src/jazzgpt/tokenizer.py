"""Event tokenizer v1: risoluzione 1 ms, vocabolario stabile e indipendente da Aria."""

from collections import defaultdict, deque

from jazzgpt.events import Note, Pedal, Performance


class EventTokenizer:
    format = "jazzgpt-events-v1"

    def __init__(self):
        self.vocabulary = ["BOS", "EOS"]
        for prefix, values in (
            ("CHANNEL", range(16)),
            ("VELOCITY", range(1, 128)),
            ("NOTE_ON", range(128)),
            ("NOTE_OFF", range(128)),
            ("PEDAL", range(128)),
            ("TIME_SHIFT", range(1, 1001)),
        ):
            self.vocabulary.extend(f"{prefix}_{i}" for i in values)
        self._ids = {token: i for i, token in enumerate(self.vocabulary)}

    @property
    def vocab_size(self) -> int:
        return len(self.vocabulary)

    def token_id(self, token: str) -> int:
        return self._ids[token]

    def encode(self, performance: Performance) -> list[int]:
        events = []
        for note in performance.notes:
            start = round(note.start * 1000)
            end = max(start + 1, round(note.end * 1000))
            events.extend(
                [
                    (start, 2, note.channel, note.pitch, note.velocity),
                    (end, 0, note.channel, note.pitch, 0),
                ]
            )
        events.extend(
            (round(p.time * 1000), 1, p.channel, p.value, 0)
            for p in sorted(performance.pedals, key=lambda p: p.time)
        )
        tokens = [self.token_id("BOS")]
        current_time = 0
        for time, kind, channel, value, velocity in sorted(events, key=lambda e: (e[0], e[1])):
            delta = time - current_time
            while delta:
                shift = min(delta, 1000)
                tokens.append(self.token_id(f"TIME_SHIFT_{shift}"))
                delta -= shift
            current_time = time
            tokens.append(self.token_id(f"CHANNEL_{channel}"))
            if kind == 2:
                tokens.append(self.token_id(f"VELOCITY_{velocity}"))
            prefix = {0: "NOTE_OFF", 1: "PEDAL", 2: "NOTE_ON"}[kind]
            tokens.append(self.token_id(f"{prefix}_{value}"))
        tokens.append(self.token_id("EOS"))
        return tokens

    def decode(self, tokens: list[int], bpm: float = 120.0) -> Performance:
        if not tokens or tokens[0] != self.token_id("BOS") or tokens[-1] != self.token_id("EOS"):
            raise ValueError("Sequenza incomplete: richiesti BOS ed EOS")
        time_ms, velocity, channel = 0, 80, 0
        active = defaultdict(deque)
        notes, pedals = [], []
        for index in tokens[1:-1]:
            if not isinstance(index, int) or not 0 <= index < self.vocab_size:
                raise ValueError(f"Token ID non valido: {index}")
            token = self.vocabulary[index]
            if token in ("BOS", "EOS"):
                raise ValueError("BOS/EOS interni alla sequenza")
            prefix, raw = token.rsplit("_", 1)
            value = int(raw)
            if prefix == "TIME_SHIFT":
                time_ms += value
            elif prefix == "CHANNEL":
                channel = value
            elif prefix == "VELOCITY":
                velocity = value
            elif prefix == "NOTE_ON":
                active[(channel, value)].append((time_ms, velocity))
            elif prefix == "NOTE_OFF":
                if not active[(channel, value)]:
                    raise ValueError("NOTE_OFF senza NOTE_ON")
                start, vel = active[(channel, value)].popleft()
                notes.append(Note(value, start / 1000, time_ms / 1000, vel, channel))
            elif prefix == "PEDAL":
                pedals.append(Pedal(time_ms / 1000, value, channel))
        if any(active.values()):
            raise ValueError("Sequenza incomplete: note ancora attive")
        return Performance(sorted(notes, key=lambda n: (n.start, n.pitch)), pedals, bpm)
