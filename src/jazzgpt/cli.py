"""CLI riproducibile, utilizzabile anche senza torch o dispositivo MIDI."""

import argparse
import importlib.util
import json
import platform
from pathlib import Path

from jazzgpt import __version__
from jazzgpt.director import STYLE_PROFILES, GenerationConfig, generate, generate_medley
from jazzgpt.ensemble import TRIO_PROGRAMS, TURN_NAMES, generate_dialogue
from jazzgpt.midi_io import list_ports, play_midi, read_midi, write_midi
from jazzgpt.tokenizer import EventTokenizer


def write_tokens(performance, path: Path):
    tokenizer = EventTokenizer()
    payload = {
        "format": tokenizer.format,
        "resolution_ms": 1,
        "bpm": performance.bpm,
        "title": performance.title,
        "vocab_size": tokenizer.vocab_size,
        "tokens": tokenizer.encode(performance),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JazzGPT: laboratorio jazz generativo")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("generate", help="Genera piano jazz con baseline leggero")
    demo.add_argument("--bars", type=int, default=8)
    demo.add_argument("--bpm", type=float, default=120)
    demo.add_argument("--key", default="C", help="Nome MIDI: C, F, Bb, F#…")
    demo.add_argument("--seed", type=int, default=42)
    demo.add_argument("--swing", type=float, default=0.64, help="0.5 dritto, circa 0.67 swing")
    demo.add_argument("--no-humanize", action="store_true")
    demo.add_argument("--output", type=Path, default=Path("renders/demo.mid"))
    demo.add_argument("--tokens", type=Path)
    demo.add_argument("--style", choices=STYLE_PROFILES, default="swing")
    medley = commands.add_parser("medley", help="Demo con due o tre stili pianistici")
    medley.add_argument(
        "--styles", nargs="+", choices=STYLE_PROFILES, default=["swing", "ballad", "latin"]
    )
    medley.add_argument("--bars-per-style", type=int, default=8)
    medley.add_argument("--bpm", type=float, default=120)
    medley.add_argument("--key", default="C")
    medley.add_argument("--seed", type=int, default=42)
    medley.add_argument(
        "--swing",
        type=float,
        default=0.64,
        help="Swing della sola sezione swing; altre sezioni a ottavi dritti",
    )
    medley.add_argument("--no-humanize", action="store_true")
    medley.add_argument("--output", type=Path, default=Path("renders/demo_styles.mid"))
    medley.add_argument("--tokens", type=Path)
    dialogue = commands.add_parser("dialogue", help="Trio: piano, basso e batteria a turno")
    dialogue.add_argument("--bars", type=int, default=16, help="Multiplo di 8")
    dialogue.add_argument("--bpm", type=float, default=120)
    dialogue.add_argument("--key", default="C")
    dialogue.add_argument("--seed", type=int, default=42)
    dialogue.add_argument("--style", choices=STYLE_PROFILES, default="swing")
    dialogue.add_argument("--swing", type=float, default=0.64)
    dialogue.add_argument("--no-humanize", action="store_true")
    dialogue.add_argument("--output", type=Path, default=Path("renders/demo_dialogue.mid"))
    dialogue.add_argument("--tokens", type=Path)
    inspect = commands.add_parser("inspect", help="Leggi note e durata di un MIDI")
    inspect.add_argument("input", type=Path)
    tokenize = commands.add_parser("tokenize", help="Converti MIDI in token eventi v1")
    tokenize.add_argument("input", type=Path)
    tokenize.add_argument("--output", type=Path, required=True)
    commands.add_parser("doctor", help="Controlla Python, architettura e backend ML opzionali")
    commands.add_parser("ports", help="Elenca porte MIDI (extra live)")
    play = commands.add_parser("play", help="Riproduci MIDI su una porta esplicita")
    play.add_argument("input", type=Path)
    play.add_argument("--port", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    try:
        if args.command in ("generate", "medley", "dialogue"):
            config = GenerationConfig(
                bars=args.bars_per_style if args.command == "medley" else args.bars,
                bpm=args.bpm,
                key=args.key,
                seed=args.seed,
                swing=args.swing,
                humanize=not args.no_humanize,
                style="swing" if args.command == "medley" else args.style,
            )
            if args.command == "generate":
                performance = generate(config)
            elif args.command == "medley":
                performance = generate_medley(config, tuple(args.styles))
            else:
                performance = generate_dialogue(config)
            write_midi(
                performance,
                args.output,
                programs=TRIO_PROGRAMS if args.command == "dialogue" else None,
            )
            if args.tokens:
                write_tokens(performance, args.tokens)
            print(
                f"Creato {args.output.resolve()} | {len(performance.notes)} note | "
                f"{performance.duration:.2f} s | baseline rule-based | seed {args.seed}"
            )
            if args.command == "medley":
                section_seconds = config.bars * 4 * 60 / config.bpm
                for index, style in enumerate(args.styles):
                    print(f"{index * section_seconds:.2f} s: {style}")
            elif args.command == "dialogue":
                for index in range(config.bars // 2):
                    print(f"{index * 8 * 60 / config.bpm:.2f} s: {TURN_NAMES[index % 4]}")
        elif args.command == "inspect":
            performance = read_midi(args.input)
            print(
                json.dumps(
                    {
                        "notes": len(performance.notes),
                        "duration_seconds": performance.duration,
                        "initial_bpm": performance.bpm,
                        "channels": sorted({n.channel for n in performance.notes}),
                        "pedal_events": len(performance.pedals),
                    },
                    indent=2,
                )
            )
        elif args.command == "tokenize":
            write_tokens(read_midi(args.input), args.output)
            print(f"Token salvati in {args.output.resolve()}")
        elif args.command == "doctor":
            info = {
                "jazzgpt": __version__,
                "python": platform.python_version(),
                "architecture": platform.machine(),
                "system": platform.platform(),
                "torch_installed": importlib.util.find_spec("torch") is not None,
                "rtmidi_installed": importlib.util.find_spec("rtmidi") is not None,
            }
            if info["torch_installed"]:
                from jazzgpt.models.torch_adapter import select_device

                info["torch_device"] = select_device()
            print(json.dumps(info, indent=2))
        elif args.command == "ports":
            print(json.dumps(list_ports(), indent=2))
        elif args.command == "play":
            play_midi(args.input, args.port)
    except (ValueError, RuntimeError, OSError, EOFError, ImportError) as exc:
        parser.exit(2, f"JazzGPT: {exc}\n")
    except KeyboardInterrupt:
        print("Riproduzione interrotta; note e pedale rilasciati.")
        return 130
    return 0
