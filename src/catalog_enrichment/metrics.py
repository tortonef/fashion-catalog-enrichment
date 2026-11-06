"""Operational metrics for the ops panel."""

from __future__ import annotations

from .tagger import ItemResult


def ops_metrics(items: list[ItemResult]) -> dict[str, float]:
    """% attributes auto-filled above the review threshold, % items needing review, avg seconds/image."""
    attrs = [a for it in items for a in it.attributes.values()]
    if not items or not attrs:
        return {"auto_filled_pct": 0.0, "flagged_items_pct": 0.0, "avg_seconds": 0.0}
    return {
        "auto_filled_pct": 100 * sum(not a.needs_review for a in attrs) / len(attrs),
        "flagged_items_pct": 100 * sum(it.needs_review for it in items) / len(items),
        "avg_seconds": sum(it.seconds for it in items) / len(items),
    }
