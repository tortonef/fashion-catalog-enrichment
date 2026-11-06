"""Normalize raw photos for the repo: rename, resize, strip ALL metadata (EXIF/GPS).

Usage: python -m catalog_enrichment.images data/images/raw data/images
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageOps

from .tagger import list_images

MAX_SIDE = 1024


def normalize_image(src: Path, dst: Path, max_side: int = MAX_SIDE) -> None:
    """Save a resized RGB JPEG copy with no metadata."""
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)  # apply camera rotation before the EXIF is dropped
        im = im.convert("RGB")
        im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        # Copy pixels into a fresh image so no EXIF, ICC, XMP or comments survive.
        clean = Image.new("RGB", im.size)
        clean.paste(im)
    clean.save(dst, "JPEG", quality=90, optimize=True)


def normalize_folder(raw_dir: Path, out_dir: Path) -> list[Path]:
    """Write item-01.jpg, item-02.jpg... into out_dir, in the raw files' name order."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for i, src in enumerate(list_images(raw_dir), start=1):
        dst = out_dir / f"item-{i:02d}.jpg"
        normalize_image(src, dst)
        written.append(dst)
    return written


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    for p in normalize_folder(Path(sys.argv[1]), Path(sys.argv[2])):
        print(p)
