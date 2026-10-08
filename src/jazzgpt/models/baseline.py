"""Scelta autoregressiva rule-based; non contiene pesi appresi."""

from math import exp
from random import Random

from jazzgpt.models.base import NoteContext


class RuleBasedModel:
    def next_pitch(self, context: NoteContext, rng: Random) -> int:
        previous = context.history[-1] if context.history else 72
        center = context.target if context.target is not None else previous
        candidates = [p for p in range(60, 85) if p % 12 in context.chord.scale]
        if len(context.history) >= 2 and context.history[-2] == previous and previous in candidates:
            candidates.remove(previous)
        scores = []
        for pitch in candidates:
            # Il motivo guida la frase; prossimità e armonia ne regolano la libertà.
            score = -0.65 * abs(pitch - center) - 0.12 * abs(pitch - previous)
            if pitch % 12 in context.chord.pitch_classes:
                score += 0.9 if context.strong_beat else 0.25
            score -= 0.55 * context.history[-4:].count(pitch)
            if abs(pitch - previous) > 7:
                score -= 1.5
            scores.append(score)
        temperature = 0.65 + 0.3 * context.tension
        peak = max(scores)
        weights = [exp((score - peak) / temperature) for score in scores]
        return rng.choices(candidates, weights=weights, k=1)[0]
