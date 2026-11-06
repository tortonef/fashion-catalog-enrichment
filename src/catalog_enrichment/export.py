"""Turn tagging results into product records (shared schema), editable tables, CSV and JSON."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

import pandas as pd
from jsonschema import Draft202012Validator

from .tagger import ItemResult

SEP = "|"  # list separator in CSV and in the editable table
LIST_FIELDS = ["colors", "materials", "occasions", "sustainability_attrs"]
# Attributes inferred from the photo, in the order shown to the user.
TAGGED_FIELDS = [
    "category",
    "gender",
    "colors",
    "pattern",
    "fit",
    "occasions",
    "season",
    "materials",
]
FIELD_ORDER = [
    "sku", "name", "brand", "category", "gender", "colors", "materials", "pattern", "fit",
    "occasions", "season", "price_eur", "sustainability_attrs", "description", "image",
]  # fmt: skip


def to_record(item: ItemResult, index: int, prefix: str = "DEMO", image: str | None = None) -> dict:
    """Build a schema record. Fields a photo cannot tell (name, brand, price...) stay null/empty."""
    rec: dict[str, Any] = {
        "sku": f"{prefix}-{index:04d}",
        "name": None,
        "brand": None,
        "price_eur": None,
        "sustainability_attrs": [],
        "description": None,
        "image": image,
    }
    for field, attr in item.attributes.items():
        rec[field] = attr.values if field in LIST_FIELDS else attr.values[0]
    return {k: rec.get(k) for k in FIELD_ORDER}


def to_frame(records: list[dict]) -> pd.DataFrame:
    """Records -> table where list fields are 'a|b' strings, so they can be edited as text."""
    rows = [{k: SEP.join(v) if k in LIST_FIELDS else v for k, v in r.items()} for r in records]
    return pd.DataFrame(rows, columns=FIELD_ORDER)


def _clean(value: Any) -> Any:
    return None if value is None or (isinstance(value, float) and pd.isna(value)) else value


def from_frame(df: pd.DataFrame) -> list[dict]:
    """Inverse of to_frame (after the user has edited the table)."""
    records = []
    for row in df.to_dict(orient="records"):
        rec = {k: _clean(row.get(k)) for k in FIELD_ORDER}
        for k in LIST_FIELDS:
            rec[k] = [s.strip() for s in str(rec[k] or "").split(SEP) if s.strip()]
        for k in ("name", "brand", "description"):
            rec[k] = rec[k] or None  # an emptied text cell means "unknown"
        if rec["price_eur"] is not None:
            rec["price_eur"] = float(rec["price_eur"])
        records.append(rec)
    return records


@cache
def _validator(schema_path: Path) -> Draft202012Validator:
    with schema_path.open(encoding="utf-8") as f:
        return Draft202012Validator(json.load(f))


def validate(records: list[dict], schema_path: Path) -> list[str]:
    """Human-readable schema errors, e.g. 'DEMO-0003 / season: 'summer' is not one of [...]'."""
    errors = []
    for rec in records:
        for err in _validator(schema_path).iter_errors(rec):
            where = "/".join(str(p) for p in err.absolute_path) or "(record)"
            errors.append(f"{rec.get('sku')} / {where}: {err.message}")
    return errors


def to_json(records: list[dict]) -> str:
    return json.dumps(records, indent=2, ensure_ascii=False)


def to_csv(records: list[dict]) -> str:
    return to_frame(records).to_csv(index=False, lineterminator="\n")
