import numpy as np
import pytest
from conftest import FakeEncoder
from PIL import Image

from catalog_enrichment.tagger import Tagger, list_images, select, softmax
from catalog_enrichment.taxonomy import Group

SINGLE = Group("pattern", ("solid", "striped", "floral"), ("p1", "p2", "p3"), False, False)
MULTI = Group("colors", ("black", "white", "red", "blue"), ("c1", "c2", "c3", "c4"), True, False)


def test_softmax_sums_to_one():
    assert softmax(np.array([1.0, 2.0, 3.0])).sum() == pytest.approx(1.0)


def test_select_single_label():
    r = select(SINGLE, np.array([0.1, 0.8, 0.1]), 0.5, 0.15, 3)
    assert r.values == ["striped"]
    assert r.confidence == pytest.approx(0.8)
    assert not r.needs_review
    assert list(r.scores) == ["striped", "solid", "floral"]


def test_select_flags_low_confidence():
    r = select(SINGLE, np.array([0.4, 0.35, 0.25]), 0.5, 0.15, 3)
    assert r.values == ["solid"]
    assert r.needs_review


def test_select_multi_label_threshold_and_top_k():
    r = select(MULTI, np.array([0.45, 0.30, 0.20, 0.05]), 0.5, 0.15, 2)
    assert r.values == ["black", "white"]  # red is above threshold but top_k=2


def test_select_multi_label_keeps_best_when_all_low():
    r = select(MULTI, np.array([0.26, 0.25, 0.25, 0.24]), 0.5, 0.3, 3)
    assert r.values == ["black"]
    assert r.needs_review


def test_tagger_picks_target_labels(groups):
    by_name = {g.name: g for g in groups}
    targets = [
        by_name["category"].prompts[by_name["category"].labels.index("jeans")],
        by_name["colors"].prompts[by_name["colors"].labels.index("navy")],
    ]
    tagger = Tagger(FakeEncoder(targets), groups)
    item = tagger.tag(Image.new("RGB", (32, 32)), "x.jpg")
    assert item.image == "x.jpg"
    assert item.attributes["category"].values == ["jeans"]
    assert item.attributes["colors"].values[0] == "navy"
    assert not item.attributes["category"].needs_review
    assert set(item.attributes) == {g.name for g in groups}
    assert item.seconds >= 0


def test_tag_paths_and_list_images(tmp_path, groups):
    for name in ["b.png", "a.jpg", "notes.txt"]:
        p = tmp_path / name
        if p.suffix == ".txt":
            p.write_text("x", encoding="utf-8")
        else:
            Image.new("RGB", (16, 16)).save(p)
    paths = list_images(tmp_path)
    assert [p.name for p in paths] == ["a.jpg", "b.png"]
    items = Tagger(FakeEncoder(["anything"]), groups).tag_paths(paths)
    assert [i.image for i in items] == ["a.jpg", "b.png"]
    assert list_images(tmp_path / "missing") == []
