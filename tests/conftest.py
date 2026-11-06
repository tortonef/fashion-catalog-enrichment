from __future__ import annotations

import zlib
from pathlib import Path

import numpy as np
import pytest

from catalog_enrichment.taxonomy import load_taxonomy

ROOT = Path(__file__).resolve().parents[1]


class FakeEncoder:
    """Deterministic stand-in for CLIP: each text gets a fixed random unit vector, and the
    'image' embedding is the normalised sum of the vectors of `target_texts`."""

    logit_scale = 100.0

    def __init__(self, target_texts: list[str] | None = None, dim: int = 256) -> None:
        self.dim = dim
        self.target_texts = target_texts or []

    def _vec(self, text: str) -> np.ndarray:
        v = np.random.default_rng(zlib.crc32(text.encode("utf-8"))).normal(size=self.dim)
        return v / np.linalg.norm(v)

    def encode_texts(self, texts: list[str]) -> np.ndarray:
        return np.stack([self._vec(t) for t in texts])

    def encode_image(self, image) -> np.ndarray:
        v = sum((self._vec(t) for t in self.target_texts), np.zeros(self.dim))
        return v / np.linalg.norm(v)


@pytest.fixture
def groups():
    return load_taxonomy(ROOT / "config" / "taxonomy.yaml")


@pytest.fixture
def schema_path() -> Path:
    return ROOT / "schema" / "product.schema.json"
