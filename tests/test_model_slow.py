"""Uses the real model from the local cache (run setup first). Excluded from CI."""

import pytest
from PIL import Image

pytestmark = pytest.mark.slow


def test_real_model_tags_an_image():
    from catalog_enrichment.factory import build_tagger

    tagger = build_tagger()
    item = tagger.tag(Image.new("RGB", (224, 224), (20, 20, 20)), "black.jpg")
    assert set(item.attributes) == {g.name for g in tagger.groups}
    assert 0 < item.attributes["category"].confidence <= 1
