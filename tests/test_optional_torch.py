"""Test aggiuntivi eseguiti solo se l'extra torch è installato."""

import pytest

torch = pytest.importorskip("torch", reason="PyTorch opzionale non installato")

from jazzgpt.models.torch_adapter import TorchTokenModel, select_device  # noqa: E402


class ConstantLogits(torch.nn.Module):
    def forward(self, inputs):
        logits = torch.full((*inputs.shape, 4), -100.0, device=inputs.device)
        logits[..., 2] = 100.0
        return logits


def test_torch_autoregression_respects_eos():
    model = TorchTokenModel(ConstantLogits(), device="cpu", context_length=2)
    assert model.generate_tokens([0, 1], eos_id=2) == [0, 1, 2]
    assert model.generate_tokens([0], max_new_tokens=3) == [0, 2, 2, 2]


def test_torch_rejects_bad_temperature():
    model = TorchTokenModel(ConstantLogits(), device="cpu")
    with pytest.raises(ValueError):
        model.generate_tokens([0], temperature=0)
    assert select_device("cpu") == "cpu"
