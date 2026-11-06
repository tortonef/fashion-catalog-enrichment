"""FashionCLIP loading. Downloads happen only in download.py (setup); the app loads offline."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
from PIL import Image

os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

# Files transformers needs; skips the ONNX export and the duplicate .bin weights.
ALLOW_PATTERNS = ["*.json", "*.txt", "model.safetensors"]
IGNORE_PATTERNS = ["onnx/*"]


def download(model_id: str, revision: str, cache_dir: Path) -> Path:
    """Fetch the pinned model snapshot into the local cache (no-op if already there)."""
    from huggingface_hub import snapshot_download

    return Path(
        snapshot_download(
            model_id,
            revision=revision,
            cache_dir=cache_dir,
            allow_patterns=ALLOW_PATTERNS,
            ignore_patterns=IGNORE_PATTERNS,
        )
    )


class ClipEncoder:
    """CLIP-style encoder running on CPU from the local cache only."""

    def __init__(self, model_id: str, revision: str, cache_dir: Path) -> None:
        import torch
        from transformers import CLIPModel, CLIPProcessor

        kwargs = {"revision": revision, "cache_dir": cache_dir, "local_files_only": True}
        try:
            self.model = CLIPModel.from_pretrained(model_id, **kwargs).eval()
            self.processor = CLIPProcessor.from_pretrained(model_id, **kwargs)
        except OSError as e:
            raise RuntimeError(
                f"Model '{model_id}' not found in {cache_dir}. Run the setup script first."
            ) from e
        self._torch = torch
        self.logit_scale = self.model.logit_scale.detach().exp().item()

    def _normalise(self, out) -> np.ndarray:
        # Older transformers return a tensor, newer ones a model output with pooled embeddings.
        t = out if isinstance(out, self._torch.Tensor) else out.pooler_output
        return (t / t.norm(dim=-1, keepdim=True)).numpy()

    def encode_texts(self, texts: list[str]) -> np.ndarray:
        with self._torch.inference_mode():
            inputs = self.processor(text=texts, return_tensors="pt", padding=True)
            return self._normalise(self.model.get_text_features(**inputs))

    def encode_image(self, image: Image.Image) -> np.ndarray:
        with self._torch.inference_mode():
            inputs = self.processor(images=image, return_tensors="pt")
            return self._normalise(self.model.get_image_features(**inputs))[0]
