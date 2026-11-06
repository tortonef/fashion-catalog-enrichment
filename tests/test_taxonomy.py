import json

from catalog_enrichment.config import load_config
from catalog_enrichment.export import TAGGED_FIELDS


def test_groups_cover_tagged_fields(groups):
    assert [g.name for g in groups] == [
        "category", "colors", "pattern", "occasions", "fit", "season", "materials", "gender"
    ]  # fmt: skip
    assert sorted(g.name for g in groups) == sorted(TAGGED_FIELDS)
    for g in groups:
        assert len(g.labels) == len(g.prompts) >= 2


def test_enum_labels_match_schema(groups, schema_path):
    props = json.loads(schema_path.read_text(encoding="utf-8"))["properties"]
    enums = {
        "category": props["category"]["enum"],
        "gender": props["gender"]["enum"],
        "season": props["season"]["enum"],
        "occasions": props["occasions"]["items"]["enum"],
    }
    by_name = {g.name: g for g in groups}
    for name, allowed in enums.items():
        assert sorted(by_name[name].labels) == sorted(allowed), name


def test_experimental_flags(groups):
    assert {g.name for g in groups if g.experimental} == {"fit", "season", "materials", "gender"}


def test_config_env_override(monkeypatch):
    monkeypatch.setenv("CATALOG_ENRICHMENT_REVIEW_THRESHOLD", "0.7")
    monkeypatch.setenv("CATALOG_ENRICHMENT_MODEL_ID", "some/other-model")
    cfg = load_config()
    assert cfg["review_threshold"] == 0.7
    assert cfg["model"]["id"] == "some/other-model"
    assert cfg["paths"]["taxonomy"].is_file()
