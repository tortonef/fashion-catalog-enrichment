import json

import pytest
from conftest import FakeEncoder
from PIL import Image

from catalog_enrichment.export import from_frame, to_csv, to_frame, to_json, to_record, validate
from catalog_enrichment.metrics import ops_metrics
from catalog_enrichment.tagger import Tagger


@pytest.fixture
def items(groups):
    tagger = Tagger(FakeEncoder(["a product photo of a dress"]), groups)
    return [tagger.tag(Image.new("RGB", (8, 8)), f"item-0{i}.jpg") for i in (1, 2)]


def test_record_is_valid_and_leaves_unknowns_empty(items, schema_path):
    rec = to_record(items[0], 1, "DEMO", "data/images/item-01.jpg")
    assert rec["sku"] == "DEMO-0001"
    assert rec["category"] == "dress"
    assert rec["name"] is None and rec["brand"] is None and rec["price_eur"] is None
    assert rec["sustainability_attrs"] == []
    assert isinstance(rec["colors"], list) and isinstance(rec["pattern"], str)
    assert validate([rec], schema_path) == []


def test_frame_round_trip_with_edits(items, schema_path):
    records = [to_record(it, i, "DEMO") for i, it in enumerate(items, 1)]
    df = to_frame(records)
    df.loc[0, "colors"] = "black | white"
    df.loc[0, "name"] = "Linen dress"
    df.loc[1, "price_eur"] = 89
    back = from_frame(df)
    assert back[0]["colors"] == ["black", "white"]
    assert back[0]["name"] == "Linen dress"
    assert back[1]["price_eur"] == 89.0
    assert back[1]["name"] is None
    assert validate(back, schema_path) == []


def test_validate_reports_bad_edits(items, schema_path):
    rec = to_record(items[0], 1)
    rec["season"] = "summer"
    rec["sku"] = "bad"
    errors = validate([rec], schema_path)
    assert any("season" in e for e in errors)
    assert any("sku" in e for e in errors)


def test_csv_and_json_exports(items):
    records = [to_record(it, i) for i, it in enumerate(items, 1)]
    assert json.loads(to_json(records)) == records
    csv_text = to_csv(records)
    assert csv_text.splitlines()[0].startswith("sku,name,brand,category")
    assert len(csv_text.splitlines()) == 3


def test_ops_metrics(items):
    items[0].seconds, items[1].seconds = 1.0, 3.0
    for a in items[0].attributes.values():
        a.needs_review = False
    m = ops_metrics(items)
    assert m["avg_seconds"] == pytest.approx(2.0)
    assert 0 <= m["auto_filled_pct"] <= 100
    assert m["flagged_items_pct"] in (0.0, 50.0, 100.0)
    assert ops_metrics([]) == {"auto_filled_pct": 0.0, "flagged_items_pct": 0.0, "avg_seconds": 0.0}
