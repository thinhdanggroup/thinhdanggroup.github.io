#!/usr/bin/env python3
"""Render a post banner from its category and slug.

    python3 script/daily_post/make_banner.py --title "..." --category python --slug my-post

Writes `banner.webp` (1600px, the post hero) and `teaser.webp` (640px, the archive
card) into `assets/images/<slug>/`, matching what `script/optimize-images/to_webp.py`
produces for hand-made art.

The banner carries NO text. Minimal Mistakes' `page__hero--overlay` (see
`_layouts/single.html` and `_includes/page__hero.html`) paints the post's own
`page__title`, description and date/read-time meta on top of `header.overlay_image`
itself, under a `rgba(0,0,0,<overlay_filter>)` darkening layer -- for every post in
this blog that is `overlay_filter: 0.5`. A banner with its own title baked in would
render the title twice, overlapping the theme's h1. So this is pure artwork: a
category-tinted gradient plus a sparse, low-alpha generative pattern seeded from the
category, title and slug, deterministic per post so two posts in the same category
look related but not identical.

Pillow only: cairosvg, rsvg-convert, ImageMagick and cwebp are all absent on the
target machine, and Pillow writes WebP natively.
"""
from __future__ import annotations

import argparse
import hashlib
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

# Running this file directly (`python3 script/daily_post/make_banner.py`, as the
# CLI is meant to be invoked) only puts this file's own directory on sys.path, not
# the repo root — so the absolute `script.daily_post.*` import below would
# otherwise fail with `ModuleNotFoundError: No module named 'script'`. Insert the
# repo root before importing our own package, matching dupe_check.py.
REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from script.daily_post.queue import CATEGORIES  # noqa: E402

BANNER_W, BANNER_H = 1600, 900
TEASER_W = 640
Q_BANNER, Q_TEASER = 80, 76

# One gradient per category, so a reader recognises the beat before reading the
# theme's own h1 title text painted on top of the banner.
CATEGORY_COLORS: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    "ai-engineering": ((26, 16, 56), (92, 46, 145)),
    "databases": ((10, 34, 44), (18, 92, 102)),
    "distributed-systems": ((12, 22, 48), (34, 74, 140)),
    "infrastructure": ((28, 24, 18), (120, 82, 34)),
    "python": ((14, 30, 40), (32, 96, 118)),
    "software-engineering": ((24, 20, 32), (86, 62, 116)),
    "web-development": ((34, 16, 28), (138, 48, 86)),
}

assert set(CATEGORY_COLORS) == set(CATEGORIES), "category colour map is out of sync"

# The theme's page__hero--overlay renders the h1/lead/meta in the vertical middle
# of the image, left-aligned within its centered content wrapper. The pattern is
# damped (not excluded — a hard-edged empty rectangle would itself look like a
# mistake) across this band so it stays calm wherever the title actually lands,
# regardless of exact wrapper width.
_TITLE_BAND = (0.22, 0.78)  # (top, bottom) as a fraction of BANNER_H
_TITLE_BAND_DAMPING = 0.35


def _gradient(size: tuple[int, int], start: tuple[int, int, int],
              end: tuple[int, int, int]) -> Image.Image:
    """A vertical linear gradient, drawn one row at a time."""
    width, height = size
    base = Image.new("RGB", size, start)
    draw = ImageDraw.Draw(base)
    for y in range(height):
        t = y / max(height - 1, 1)
        draw.line(
            [(0, y), (width, y)],
            fill=tuple(round(s + (e - s) * t) for s, e in zip(start, end)),
        )
    return base


def _pattern_seed(category: str, title: str, slug: str) -> int:
    """A stable integer seed from category + title + slug.

    Uses sha256 rather than Python's built-in `hash()`, which is salted per
    process (`PYTHONHASHSEED`) and would make the "same input, same output"
    guarantee false across reruns and machines.
    """
    material = f"{category}|{title}|{slug}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def _damp(y: float, height: int) -> float:
    top, bottom = _TITLE_BAND[0] * height, _TITLE_BAND[1] * height
    return _TITLE_BAND_DAMPING if top <= y <= bottom else 1.0


def _pattern_overlay(size: tuple[int, int], seed: int) -> Image.Image:
    """A sparse, low-alpha generative pattern: a few soft blurred blobs, thin
    scattered lines, and small dots — restrained by design.

    This sits under the theme's white h1/lead text at 50% black darkening
    (`header.overlay_filter: 0.5`), so nothing here may compete with that text:
    every element is drawn at low alpha, and further damped across the vertical
    band where the title actually renders. Restrained also matters for the
    *undarkened* teaser thumbnail — a loud pattern would look like clip art at
    small size, not deliberate art direction.
    """
    width, height = size
    rng = random.Random(seed)
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))

    # A handful of large, soft blobs — blurred after drawing so their edges
    # dissolve into the gradient rather than reading as flat circles.
    draw = ImageDraw.Draw(overlay)
    for _ in range(rng.randint(3, 5)):
        cx, cy = rng.uniform(0, width), rng.uniform(0, height)
        r = rng.uniform(90, 220)
        alpha = round(rng.uniform(10, 20) * _damp(cy, height))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, alpha))
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=70))

    # Sparse thin lines, drawn crisp (after the blur) so they read as deliberate
    # geometry rather than more soft haze.
    draw = ImageDraw.Draw(overlay)
    for _ in range(rng.randint(6, 10)):
        x1, y1 = rng.uniform(0, width), rng.uniform(0, height)
        x2 = x1 + rng.uniform(180, 520) * rng.choice((-1, 1))
        y2 = y1 + rng.uniform(-200, 200)
        alpha = round(rng.uniform(12, 24) * _damp((y1 + y2) / 2, height))
        draw.line([(x1, y1), (x2, y2)], fill=(255, 255, 255, alpha),
                  width=rng.choice((1, 1, 2)))

    # A light scatter of small dots for texture.
    for _ in range(rng.randint(14, 20)):
        cx, cy = rng.uniform(0, width), rng.uniform(0, height)
        r = rng.uniform(2, 5)
        alpha = round(rng.uniform(18, 36) * _damp(cy, height))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, alpha))

    return overlay


def render_banner(title: str, category: str, out_dir: Path) -> tuple[Path, Path]:
    """Write banner.webp and teaser.webp into `out_dir`. Returns both paths.

    Pure artwork, no text: a category gradient plus a generative pattern seeded
    from `category`, `title`, and `out_dir`'s name (the post slug in normal CLI
    use), so a rerun for the same post is byte-identical while different posts
    — even same-category, same-title-length posts — visibly differ.
    """
    if category not in CATEGORY_COLORS:
        raise ValueError(
            f"unknown category {category!r}; allowed: {sorted(CATEGORY_COLORS)}"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    start, end = CATEGORY_COLORS[category]
    base = _gradient((BANNER_W, BANNER_H), start, end).convert("RGBA")

    seed = _pattern_seed(category, title, out_dir.name)
    overlay = _pattern_overlay((BANNER_W, BANNER_H), seed)
    image = Image.alpha_composite(base, overlay).convert("RGB")

    banner_path = out_dir / "banner.webp"
    image.save(banner_path, "WEBP", quality=Q_BANNER, method=6)

    teaser_height = round(BANNER_H * TEASER_W / BANNER_W)
    teaser_path = out_dir / "teaser.webp"
    image.resize((TEASER_W, teaser_height), Image.LANCZOS).save(
        teaser_path, "WEBP", quality=Q_TEASER, method=6
    )

    return banner_path, teaser_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", required=True)
    parser.add_argument("--category", required=True, choices=sorted(CATEGORY_COLORS))
    parser.add_argument("--slug", required=True)
    parser.add_argument("--assets-dir", default=str(REPO / "assets" / "images"))
    args = parser.parse_args()

    banner, teaser = render_banner(
        args.title, args.category, Path(args.assets_dir) / args.slug
    )
    print(banner.relative_to(REPO) if banner.is_relative_to(REPO) else banner)
    print(teaser.relative_to(REPO) if teaser.is_relative_to(REPO) else teaser)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
