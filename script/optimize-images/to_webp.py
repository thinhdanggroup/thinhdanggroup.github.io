#!/usr/bin/env python3
"""Generate the WebP derivatives every post banner needs.

    python script/optimize-images/to_webp.py assets/images/my-post-slug
    python script/optimize-images/to_webp.py assets/images/my-post/banner.png
    python script/optimize-images/to_webp.py --all          # whole library

For a file named `banner.*` this writes both `banner.webp` (1600px, the post
hero) and `teaser.webp` (640px, the archive card). Any other image over the size
threshold just gets a same-name `.webp` sibling. Originals are never modified.

Requires Pillow:  pip install Pillow
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required:  pip install Pillow")

MAX_W_FULL = 1600
MAX_W_TEASER = 640
Q_FULL = 80
Q_TEASER = 76
MIN_BYTES = 150 * 1024
RASTER = {".png", ".jpg", ".jpeg"}

REPO = Path(__file__).resolve().parents[2]


def encode(src: Path, dst: Path, max_w: int, quality: int) -> int:
    im = Image.open(src)
    im.load()
    if im.mode in ("P", "LA"):
        im = im.convert("RGBA")
    elif im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGB")
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, "WEBP", quality=quality, method=6)
    return dst.stat().st_size


def collect(targets: list[str], everything: bool) -> list[Path]:
    if everything:
        return sorted(
            p for p in (REPO / "assets" / "images").rglob("*")
            if p.suffix.lower() in RASTER
        )
    out: list[Path] = []
    for t in targets:
        p = Path(t)
        if not p.is_absolute():
            p = REPO / p
        if p.is_dir():
            out += sorted(q for q in p.rglob("*") if q.suffix.lower() in RASTER)
        elif p.is_file() and p.suffix.lower() in RASTER:
            out.append(p)
        else:
            print(f"skip (not an image): {t}", file=sys.stderr)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="*", help="image files or directories")
    ap.add_argument("--all", action="store_true", help="process assets/images entirely")
    ap.add_argument("--force", action="store_true",
                    help="ignore the %dKB size threshold" % (MIN_BYTES // 1024))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.targets and not args.all:
        ap.error("pass a path, or --all")

    images = collect(args.targets, args.all)
    if not images:
        print("nothing to do")
        return 0

    before = after = 0
    made = skipped = 0

    for src in images:
        orig = src.stat().st_size
        if orig < MIN_BYTES and not args.force:
            skipped += 1
            continue

        rel = src.relative_to(REPO)
        if args.dry_run:
            print(f"would convert {rel} ({orig/1024:.0f}KB)")
            made += 1
            continue

        full = src.with_suffix(".webp")
        size = encode(src, full, MAX_W_FULL, Q_FULL)
        if size >= orig:
            full.unlink(missing_ok=True)
            print(f"skip {rel}: webp is not smaller")
            skipped += 1
            continue

        before += orig
        after += size
        made += 1
        line = f"{rel}  {orig/1024:.0f}KB -> {size/1024:.0f}KB"

        if src.stem == "banner":
            tsr = src.with_name("teaser.webp")
            tsize = encode(src, tsr, MAX_W_TEASER, Q_TEASER)
            after += tsize
            line += f"  (+ teaser.webp {tsize/1024:.0f}KB)"
        print(line)

    print(f"\nconverted {made}, skipped {skipped}")
    if before and not args.dry_run:
        print(f"{before/1048576:.1f} MB -> {after/1048576:.1f} MB "
              f"({100 * (1 - after / before):.0f}% smaller)")
        print("\nRemember to point the post's front matter at the .webp files:")
        print("  overlay_image: /assets/images/<slug>/banner.webp")
        print("  teaser:        /assets/images/<slug>/teaser.webp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
