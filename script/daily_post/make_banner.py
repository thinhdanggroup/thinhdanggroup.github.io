#!/usr/bin/env python3
"""Render a post banner from its title and category.

    python3 script/daily_post/make_banner.py --title "..." --category python --slug my-post

Writes `banner.webp` (1600px, the post hero) and `teaser.webp` (640px, the archive
card) into `assets/images/<slug>/`, matching what `script/optimize-images/to_webp.py`
produces for hand-made art.

Pillow only: cairosvg, rsvg-convert, ImageMagick and cwebp are all absent on the
target machine, and Pillow writes WebP natively.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

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

# Font candidates in preference order. Inter matches the site; DejaVu is the
# fallback that exists on essentially every Linux box, so a machine without Inter
# still renders rather than crashing the daily run.
FONT_CANDIDATES = (
    "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)

# One gradient per category, so a reader recognises the beat before reading the title.
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


def resolve_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """The first available font candidate at `size`, or Pillow's built-in default."""
    for candidate in FONT_CANDIDATES:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default(size)


def wrap_title(
    title: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    max_lines: int = 4,
) -> list[str]:
    """Greedy word wrap, truncated with an ellipsis past `max_lines`.

    A word longer than the line budget is placed on its own line rather than
    looping forever trying to fit it.
    """
    words = title.split()
    lines: list[str] = []
    current = ""

    for word in words:
        trial = f"{current} {word}".strip()
        if font.getbbox(trial)[2] <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
        if len(lines) == max_lines:
            break

    if current and len(lines) < max_lines:
        lines.append(current)

    if len(lines) == max_lines:
        consumed = len(" ".join(lines).split())
        if consumed < len(words):
            lines[-1] = _ellipsise(lines[-1], font, max_width)

    return lines


def _ellipsise(line: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    text = line.rstrip() + "…"
    while font.getbbox(text)[2] > max_width and " " in text:
        text = text.rsplit(" ", 1)[0].rstrip() + "…"
    return text


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


def render_banner(title: str, category: str, out_dir: Path) -> tuple[Path, Path]:
    """Write banner.webp and teaser.webp into `out_dir`. Returns both paths."""
    if category not in CATEGORY_COLORS:
        raise ValueError(
            f"unknown category {category!r}; allowed: {sorted(CATEGORY_COLORS)}"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    start, end = CATEGORY_COLORS[category]
    image = _gradient((BANNER_W, BANNER_H), start, end)
    draw = ImageDraw.Draw(image)

    margin = 120
    text_width = BANNER_W - 2 * margin

    title_font = resolve_font(96)
    lines = wrap_title(title, title_font, text_width)
    line_height = round(96 * 1.22)

    block_height = line_height * len(lines)
    y = (BANNER_H - block_height) // 2
    for line in lines:
        draw.text((margin, y), line, font=title_font, fill=(255, 255, 255))
        y += line_height

    # Category label under the title, tracked out and dimmed so it reads as
    # metadata. A pre-dimmed solid RGB colour, not RGBA: this image is mode
    # "RGB", and Pillow raises if draw.text() is given a 4-tuple fill on an
    # RGB image (CONTROLLER NOTE Ruling F1).
    label_font = resolve_font(34)
    draw.text(
        (margin, y + 28),
        category.replace("-", " ").upper(),
        font=label_font,
        fill=(214, 214, 224),
    )

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
