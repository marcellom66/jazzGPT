"""Bridge per Aria: il backend deve utilizzare i token e pesi ufficiali."""

from jazzgpt.events import Performance
from jazzgpt.models.base import ContinuationBackend


class AriaAdapter:
    def __init__(self, backend: ContinuationBackend | None = None):
        self.backend = backend

    def generate(self, prompt: Performance, max_new_tokens: int = 512) -> Performance:
        if self.backend is None:
            raise NotImplementedError(
                "Aria richiede un backend reale con tokenizer, configurazione e checkpoint "
                "ufficiali. Implementa ContinuationBackend.continue_midi; "
                "il tokenizer JazzGPT non è compatibile con i token Aria."
            )
        if max_new_tokens < 1:
            raise ValueError("max_new_tokens deve essere positivo")
        return self.backend.continue_midi(prompt, max_new_tokens)
