"""File MIDI e porte live opzionali. mido obbligatorio, rtmidi solo per hardware."""

from collections import defaultdict, deque
from pathlib import Path
from time import monotonic, sleep

import mido

from jazzgpt.events import Note, Pedal, Performance


def write_midi(
    performance: Performance,
    path: str | Path,
    ticks_per_beat: int = 960,
    *,
    programs: dict[int, int] | None = None,
) -> Path:
    programs = {} if programs is None else programs
    if any(
        not isinstance(channel, int)
        or not 0 <= channel <= 15
        or not isinstance(program, int)
        or not 0 <= program <= 127
        for channel, program in programs.items()
    ):
        raise ValueError("Canali e programmi MIDI devono essere interi nei rispettivi limiti")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    midi = mido.MidiFile(type=1, ticks_per_beat=ticks_per_beat)
    track = mido.MidiTrack()
    midi.tracks.append(track)
    tempo = mido.bpm2tempo(performance.bpm)
    # MIDI text defaults to Latin-1 in mido; arbitrary Unicode must not break export.
    midi_title = performance.title.encode("latin-1", errors="replace").decode("latin-1")
    track.extend(
        [
            mido.MetaMessage("track_name", name=midi_title),
            mido.MetaMessage("set_tempo", tempo=tempo),
            mido.MetaMessage("time_signature", numerator=4, denominator=4),
        ]
    )
    channels = sorted(
        {n.channel for n in performance.notes} | {p.channel for p in performance.pedals}
    )
    for channel in channels:
        track.append(
            mido.Message("program_change", program=programs.get(channel, 0), channel=channel)
        )

    def tick(seconds):
        return round(mido.second2tick(seconds, ticks_per_beat, tempo))

    events = []
    for note in performance.notes:
        start, end = tick(note.start), max(tick(note.start) + 1, tick(note.end))
        events.extend(
            [
                (
                    start,
                    2,
                    mido.Message(
                        "note_on", note=note.pitch, velocity=note.velocity, channel=note.channel
                    ),
                ),
                (
                    end,
                    0,
                    mido.Message("note_off", note=note.pitch, velocity=0, channel=note.channel),
                ),
            ]
        )
    pedal_state = {}
    for pedal in sorted(performance.pedals, key=lambda p: p.time):
        events.append(
            (
                tick(pedal.time),
                1,
                mido.Message(
                    "control_change", control=64, value=pedal.value, channel=pedal.channel
                ),
            )
        )
        pedal_state[pedal.channel] = pedal.value
    final_tick = max([tick(performance.duration)] + [event[0] for event in events])
    for channel, value in pedal_state.items():
        if value >= 64:
            events.append(
                (
                    final_tick,
                    3,
                    mido.Message("control_change", control=64, value=0, channel=channel),
                )
            )
    previous = 0
    for absolute, _, message in sorted(events, key=lambda e: (e[0], e[1])):
        track.append(message.copy(time=absolute - previous))
        previous = absolute
    track.append(mido.MetaMessage("end_of_track", time=0))
    midi.save(path)
    return path


def read_midi(path: str | Path) -> Performance:
    midi = mido.MidiFile(path)
    if midi.type == 2:
        raise ValueError("MIDI tipo 2 con sequenze indipendenti non supportato")
    active = defaultdict(deque)
    notes, pedals = [], []
    time, bpm = 0.0, 120.0
    for message in midi:  # mido applica i cambi di tempo e restituisce delta in secondi.
        time += message.time
        if message.type == "set_tempo":
            # Senza tempo a t=0, il MIDI parte a 120 BPM. A t=0 vale l'ultimo tempo.
            if time == 0:
                bpm = mido.tempo2bpm(message.tempo)
        elif message.type == "note_on" and message.velocity > 0:
            active[(message.channel, message.note)].append((time, message.velocity))
        elif message.type == "note_off" or (message.type == "note_on" and message.velocity == 0):
            queue = active[(message.channel, message.note)]
            if queue:
                start, velocity = queue.popleft()
                if time > start:
                    notes.append(Note(message.note, start, time, velocity, message.channel))
        elif message.type == "control_change" and message.control == 64:
            pedals.append(Pedal(time, message.value, message.channel))
    if any(active.values()):
        raise ValueError("MIDI incompleto: mancano note-off")
    return Performance(
        sorted(notes, key=lambda n: (n.start, n.pitch)), pedals, bpm, Path(path).stem
    )


def live_backend():
    try:
        import rtmidi  # noqa: F401
    except ImportError as exc:
        raise RuntimeError('Installa le porte MIDI con: pip install -e ".[live]"') from exc
    return mido.Backend("mido.backends.rtmidi")


def list_ports() -> dict[str, list[str]]:
    backend = live_backend()
    return {"inputs": backend.get_input_names(), "outputs": backend.get_output_names()}


def play_midi(path: str | Path, port_name: str) -> None:
    """Riproduce un file su una porta esplicita, rilasciando note e sustain in uscita."""
    backend = live_backend()
    with backend.open_output(port_name) as port:
        try:
            deadline = monotonic()
            for message in mido.MidiFile(path):
                deadline += message.time
                sleep(max(0, deadline - monotonic()))
                if not message.is_meta:
                    port.send(message.copy(time=0))
        finally:
            for channel in range(16):
                port.send(mido.Message("control_change", control=64, value=0, channel=channel))
                port.send(mido.Message("control_change", control=123, value=0, channel=channel))
