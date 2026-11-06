"""Smoke check run at the end of setup: model loads offline, tags an image, output fits the schema."""

from __future__ import annotations

from PIL import Image

from .config import load_config
from .export import to_record, validate
from .factory import build_tagger
from .tagger import list_images


def main() -> None:
    cfg = load_config()
    tagger = build_tagger(cfg)
    samples = list_images(cfg["paths"]["images"])
    if samples:
        with Image.open(samples[0]) as im:
            item = tagger.tag(im, samples[0].name)
    else:
        item = tagger.tag(Image.new("RGB", (224, 224), (180, 40, 40)), "synthetic")
    errors = validate([to_record(item, 1, cfg["sku_prefix"])], cfg["paths"]["schema"])
    if errors:
        raise SystemExit("Smoke check failed:\n" + "\n".join(errors))
    summary = ", ".join(f"{k}={'/'.join(a.values)}" for k, a in item.attributes.items())
    print(f"Smoke check OK ({item.seconds:.2f} s): {item.image}: {summary}")


if __name__ == "__main__":
    main()
