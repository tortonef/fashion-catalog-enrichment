import pytest
from PIL import Image

from catalog_enrichment.evaluate import load_labels, render, score
from catalog_enrichment.images import normalize_folder
from catalog_enrichment.taxonomy import Group


def test_normalize_strips_exif_resizes_and_rotates(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    exif = Image.Exif()
    exif[0x0112] = 6  # orientation: rotate 90 degrees
    exif[0x010F] = "PhoneMaker"
    exif.get_ifd(0x8825)[2] = (45.0, 27.0, 0.0)  # GPS latitude
    Image.new("RGB", (3000, 2000), (200, 30, 30)).save(raw / "IMG_2.jpg", exif=exif)
    Image.new("RGB", (500, 400)).save(raw / "IMG_1.png")

    out = normalize_folder(raw, tmp_path / "out")

    assert [p.name for p in out] == ["item-01.jpg", "item-02.jpg"]
    with Image.open(out[1]) as im:
        assert im.size == (683, 1024)  # rotated to portrait, long side 1024
        assert len(im.getexif()) == 0
        assert "exif" not in im.info and "icc_profile" not in im.info
    with Image.open(out[0]) as im:
        assert im.size == (500, 400)  # small images are not upscaled


def test_score_single_and_multi():
    groups = [
        Group("category", ("dress", "jeans"), ("a", "b"), False, False),
        Group("colors", ("black", "white", "red"), ("a", "b", "c"), True, False),
    ]
    truth = {
        "1.jpg": {"category": {"dress"}, "colors": {"black", "white"}},
        "2.jpg": {"category": {"jeans"}, "colors": {"red"}},
    }
    preds = {
        "1.jpg": {"category": {"dress"}, "colors": {"black"}},
        "2.jpg": {"category": {"dress"}, "colors": {"red", "white"}},
    }
    rows = {r["attribute"]: r for r in score(preds, truth, groups)}
    assert rows["category"]["accuracy"] == pytest.approx(0.5)
    assert rows["colors"]["precision"] == pytest.approx(2 / 3)
    assert rows["colors"]["recall"] == pytest.approx(2 / 3)
    md = render(list(rows.values()), 2, 0.4, "some/model")
    assert "| category | single-label | 2 | 50% |" in md


def test_load_labels(tmp_path):
    p = tmp_path / "labels.csv"
    p.write_text("image,category,colors\nitem-01.jpg,jeans,navy|white\n", encoding="utf-8")
    assert load_labels(p) == {"item-01.jpg": {"category": {"jeans"}, "colors": {"navy", "white"}}}
