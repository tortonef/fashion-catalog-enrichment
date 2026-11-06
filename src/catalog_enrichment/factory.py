"""Build a ready-to-use Tagger from config.yaml."""

from __future__ import annotations

from typing import Any

from .config import load_config
from .model import ClipEncoder
from .tagger import Tagger
from .taxonomy import load_taxonomy


def build_tagger(cfg: dict[str, Any] | None = None) -> Tagger:
    """Load the cached model and the taxonomy (no network access)."""
    cfg = cfg or load_config()
    m = cfg["model"]
    return Tagger(
        ClipEncoder(m["id"], m["revision"], m["cache_dir"]),
        load_taxonomy(cfg["paths"]["taxonomy"]),
        review_threshold=float(cfg["review_threshold"]),
        multi_threshold=float(cfg["multi_label_threshold"]),
        top_k=int(cfg["multi_label_top_k"]),
    )
