"""Campionatore per un modello PyTorch iniettato, senza caricare checkpoint impliciti."""

from collections.abc import Callable
from math import isfinite


def select_device(requested: str = "auto") -> str:
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError('PyTorch opzionale assente: pip install -e ".[torch]"') from exc
    if requested not in ("auto", "cpu", "mps"):
        raise ValueError("device deve essere auto, cpu o mps")
    available = torch.backends.mps.is_available()
    if requested == "mps" and not available:
        raise RuntimeError("MPS non disponibile; scegli cpu o verifica Python ARM64/macOS")
    return ("mps" if available else "cpu") if requested == "auto" else requested


class TorchTokenModel:
    """forward(input_ids) -> Tensor [1, T, V], oppure output.logits.

    Non è direttamente un NoteModel: serve un decoder/adattatore da eventi a note.
    Callable logits_fn può adattare il forward di un modello esterno.
    """

    def __init__(
        self,
        model,
        device: str = "auto",
        context_length: int = 1024,
        logits_fn: Callable | None = None,
    ):
        if context_length < 1:
            raise ValueError("context_length deve essere positivo")
        self.device = select_device(device)
        self.model = model.to(self.device).eval()
        self.context_length = context_length
        self.logits_fn = logits_fn or self.model

    def generate_tokens(
        self,
        prompt: list[int],
        max_new_tokens: int = 64,
        temperature: float = 0.9,
        eos_id: int | None = None,
        seed: int = 42,
    ) -> list[int]:
        import torch

        if not prompt or any(not isinstance(i, int) or i < 0 for i in prompt):
            raise ValueError("Il prompt deve contenere token ID non negativi")
        if not isfinite(temperature) or temperature <= 0 or max_new_tokens < 1:
            raise ValueError("temperature e max_new_tokens devono essere positivi")
        # Campionamento CPU con generator locale: nessuna modifica del seed globale.
        rng = torch.Generator(device="cpu").manual_seed(seed)
        sequence = list(prompt)
        with torch.inference_mode():
            for _ in range(max_new_tokens):
                inputs = torch.tensor(
                    [sequence[-self.context_length :]], dtype=torch.long, device=self.device
                )
                output = self.logits_fn(inputs)
                logits = output.logits if hasattr(output, "logits") else output
                if logits.ndim != 3 or logits.shape[:2] != inputs.shape:
                    raise ValueError("Il modello deve restituire logits [1, T, V]")
                scores = logits[0, -1].float().cpu() / temperature
                if not torch.isfinite(scores).all():
                    raise ValueError("Logits non finiti")
                next_id = int(torch.multinomial(torch.softmax(scores, dim=-1), 1, generator=rng))
                sequence.append(next_id)
                if next_id == eos_id:
                    break
        return sequence
