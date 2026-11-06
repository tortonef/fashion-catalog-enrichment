"""Attribute groups and their zero-shot labels, read from config/taxonomy.yaml."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Group:
    name: str
    labels: tuple[str, ...]  # values written to the product record
    prompts: tuple[str, ...]  # text shown to the model, same order as labels
    multi: bool
    experimental: bool


def load_taxonomy(path: Path) -> list[Group]:
    """Parse the taxonomy file into groups, keeping file order."""
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)["groups"]
    groups = []
    for name, spec in raw.items():
        labels = {str(k): v for k, v in spec["labels"].items()}
        if not labels:
            raise ValueError(f"Taxonomy group '{name}' has no labels")
        groups.append(
            Group(
                name=name,
                labels=tuple(labels),
                prompts=tuple(spec["template"].format(v) for v in labels.values()),
                multi=bool(spec.get("multi", False)),
                experimental=bool(spec.get("experimental", False)),
            )
        )
    return groups
