"""Zero-shot attribute tagging: compare one image against the text prompts of every attribute group."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import numpy as np
from PIL import Image

from .taxonomy import Group

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


class Encoder(Protocol):
    """Anything that embeds images and texts in the same space (L2-normalised rows)."""

    logit_scale: float

    def encode_texts(self, texts: list[str]) -> np.ndarray: ...

    def encode_image(self, image: Image.Image) -> np.ndarray: ...


@dataclass
class AttributeResult:
    group: str
    values: list[str]  # one value for single-label groups, one or more for multi-label groups
    confidence: float  # probability of the top label
    scores: dict[str, float]  # every label's probability, highest first
    experimental: bool
    needs_review: bool


@dataclass
class ItemResult:
    image: str
    attributes: dict[str, AttributeResult] = field(default_factory=dict)
    seconds: float = 0.0

    @property
    def needs_review(self) -> bool:
        """Flag the item only for low confidence on core attributes: experimental ones are
        almost always uncertain, so counting them would flag every item."""
        return any(a.needs_review and not a.experimental for a in self.attributes.values())


def softmax(logits: np.ndarray) -> np.ndarray:
    exp = np.exp(logits - logits.max())
    return exp / exp.sum()


def select(
    group: Group, probs: np.ndarray, review_threshold: float, multi_threshold: float, top_k: int
) -> AttributeResult:
    """Turn label probabilities into the attribute value(s), confidence and review flag."""
    order = np.argsort(-probs)
    confidence = float(probs[order[0]])
    if group.multi:
        # Always keep the best label, then any other label above the threshold, up to top_k.
        keep = [i for i in order[:top_k] if probs[i] >= multi_threshold] or [order[0]]
        values = [group.labels[i] for i in keep]
    else:
        values = [group.labels[order[0]]]
    return AttributeResult(
        group=group.name,
        values=values,
        confidence=confidence,
        scores={group.labels[i]: float(probs[i]) for i in order},
        experimental=group.experimental,
        needs_review=confidence < review_threshold,
    )


class Tagger:
    """Tags images against a taxonomy; text prompts are embedded once at start-up."""

    def __init__(
        self,
        encoder: Encoder,
        groups: list[Group],
        review_threshold: float = 0.5,
        multi_threshold: float = 0.15,
        top_k: int = 3,
    ) -> None:
        self.encoder = encoder
        self.groups = groups
        self.review_threshold = review_threshold
        self.multi_threshold = multi_threshold
        self.top_k = top_k
        self._text = {g.name: encoder.encode_texts(list(g.prompts)) for g in groups}

    def tag(self, image: Image.Image, name: str = "") -> ItemResult:
        """Tag one image with every attribute group."""
        start = time.perf_counter()
        img = self.encoder.encode_image(image.convert("RGB"))
        result = ItemResult(image=name)
        for g in self.groups:
            probs = softmax(self.encoder.logit_scale * (self._text[g.name] @ img))
            result.attributes[g.name] = select(
                g, probs, self.review_threshold, self.multi_threshold, self.top_k
            )
        result.seconds = time.perf_counter() - start
        return result

    def tag_paths(self, paths: list[Path]) -> list[ItemResult]:
        """Tag several image files (batch mode)."""
        results = []
        for p in paths:
            with Image.open(p) as im:
                results.append(self.tag(im, p.name))
        return results


def list_images(folder: Path) -> list[Path]:
    """Image files directly inside a folder, sorted by name."""
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
