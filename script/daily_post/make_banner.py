#!/usr/bin/env python3
"""Render a post banner from its category and slug.

    python3 script/daily_post/make_banner.py --title "..." --category python --slug my-post

Writes `banner.webp` (1600px, the post hero), `teaser.webp` (640px, the archive
card) and `banner.svg` (the vector source both rasters are rendered from) into
`assets/images/<slug>/`. The two WebP files match what
`script/optimize-images/to_webp.py` produces for hand-made art.

The banner carries NO text. Minimal Mistakes' `page__hero--overlay` (see
`_layouts/single.html` and `_includes/page__hero.html`) paints the post's own
`page__title`, description and date/read-time meta on top of `header.overlay_image`
itself, under a `rgba(0,0,0,<overlay_filter>)` darkening layer -- for every post in
this blog that is `overlay_filter: 0.5`. A banner with its own title baked in would
render the title twice, overlapping the theme's h1. So this is pure artwork: a
category-tinted gradient plus a sparse, low-opacity generative composition seeded
from the category, title and slug, deterministic per post so two posts in the same
category look related but not identical.

Two renderers, in preference order:

* **SVG + cairosvg** (preferred). The artwork is authored as SVG and rasterised
  with `cairosvg`. SVG buys real radial gradients, multi-stop ramps, per-element
  opacity, clip paths and bezier strokes of varying width -- none of which Pillow's
  primitives offer -- and the vector source ships next to the rasters as
  `banner.svg`, so the art stays editable after the fact.
* **Pillow only** (fallback). If `cairosvg` cannot be imported -- a cron box
  without libcairo, say -- the original Pillow composition renders instead and a
  note goes to stderr. This path is kept working and tested on purpose: this
  pipeline has twice been bitten by a tool that was installed but unavailable at
  runtime, and a banner is not worth failing a whole run over.

Constraints that hold for BOTH renderers, each pinned by a test in
`tests/test_make_banner.py`:

* no text, ever (see above);
* deterministic -- same title/category/slug, byte-identical output, across
  processes and `PYTHONHASHSEED` values (hence `hashlib.sha256`, never `hash()`);
* per-slug variation -- two posts in the same category must not collide;
* WCAG AA in the title band -- simulate the theme's 50% black overlay and white
  title text must still clear 4.5:1 against the busiest pixel there;
* the teaser is shown UNDARKENED as a small archive thumbnail, so the composition
  has to read raw and at 640px too.

What cairosvg does NOT support, verified by probe against 2.9.1 -- do not reach
for these, they fail silently to black or to a no-op: `feGaussianBlur` (renders
unblurred), `feTurbulence` (renders black), `<mask>` (ignored), and a gradient
paint on a `stroke` (renders nothing). Softness here comes from multi-stop radial
gradients instead, which is the better tool anyway.
"""
from __future__ import annotations

import argparse
import hashlib
import io
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
TEASER_H = round(BANNER_H * TEASER_W / BANNER_W)
Q_BANNER, Q_TEASER = 80, 76

# One gradient per category, so a reader recognises the beat before reading the
# theme's own h1 title text painted on top of the banner. Every other colour in
# the composition — wash, aurora, rings, arcs, dots — is derived from this pair,
# so retuning a category is a one-line change here and nothing else drifts.
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


# ---------------------------------------------------------------------------
# shared: seeding and the title-band damping
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# the SVG renderer (preferred)
# ---------------------------------------------------------------------------


def _n(value: float) -> str:
    """Format a number for SVG at fixed precision, so the document text is
    stable across machines and no float-repr quirk can break determinism."""
    text = f"{value:.2f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _rgb(color: tuple[int, int, int]) -> str:
    r, g, b = (max(0, min(255, round(c))) for c in color)
    return f"#{r:02x}{g:02x}{b:02x}"


def _mix(a: tuple[int, int, int], b: tuple[int, int, int],
         t: float) -> tuple[int, int, int]:
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def _soft_damp(y: float) -> float:
    """The title band's damping, as a continuous curve rather than a step.

    The Pillow path damps with a hard boundary because it composites discrete
    shapes; in SVG everything is a smooth ramp anyway, so the damping ramps too
    — `_TITLE_BAND_DAMPING` across the band, full strength beyond a shoulder
    either side. A step function would leave a visible seam across the artwork.
    """
    top, bottom = _TITLE_BAND
    shoulder = 0.10
    t = y / BANNER_H
    if top <= t <= bottom:
        return _TITLE_BAND_DAMPING
    k = min(1.0, (top - t) / shoulder) if t < top else min(1.0, (t - bottom) / shoulder)
    return _TITLE_BAND_DAMPING + (1.0 - _TITLE_BAND_DAMPING) * k


def build_svg(title: str, category: str, slug: str) -> str:
    """The banner as an SVG document: the authored source, not a rasterisation.

    Layers, back to front:

      1. the category ramp — a three-stop vertical gradient that holds the dark
         start colour through the upper half before opening up to the end
         colour, so the recognisable category tint is still read first;
      2. a diagonal accent wash anchored to a seeded corner, giving the flat
         vertical ramp a direction of light;
      3. two to four aurora ellipses, each a three-stop radial gradient, rotated
         and elongated — the soft shapes the Pillow path could only approximate
         by drawing flat circles and blurring the whole overlay;
      4. concentric rings anchored off-canvas and clipped to the frame, as quiet
         geometry under the haze;
      5. long quadratic-bezier arcs at varying stroke width;
      6. a sparse dot scatter for texture;
      7. a scrim across the title band and a vignette — both buy back WCAG
         headroom for the theme's white h1 while reading as art direction rather
         than as a correction.

    Nothing here is text, and nothing here is an icon.
    """
    if category not in CATEGORY_COLORS:
        raise ValueError(
            f"unknown category {category!r}; allowed: {sorted(CATEGORY_COLORS)}"
        )

    start, end = CATEGORY_COLORS[category]
    rng = random.Random(_pattern_seed(category, title, slug))

    mid = _mix(start, end, 0.42)
    accent = _mix(end, (255, 255, 255), 0.30)   # the lit tint
    haze = _mix(end, (255, 255, 255), 0.62)     # near-white, still category-tinted
    W, H = BANNER_W, BANNER_H

    defs: list[str] = []
    body: list[str] = []

    # --- 1. the category ramp ----------------------------------------------
    defs.append(
        '<linearGradient id="ramp" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{_rgb(start)}"/>'
        f'<stop offset="0.58" stop-color="{_rgb(mid)}"/>'
        f'<stop offset="1" stop-color="{_rgb(end)}"/>'
        "</linearGradient>"
    )
    body.append(f'<rect width="{W}" height="{H}" fill="url(#ramp)"/>')

    # --- 2. the diagonal accent wash ---------------------------------------
    # Which corner the light comes from is seeded, so same-category posts differ
    # in their overall read, not only in the scatter of small elements.
    corner = rng.choice(((0, 0, 1, 1), (1, 0, 0, 1), (0, 1, 1, 0), (1, 1, 0, 0)))
    wash_alpha = rng.uniform(0.16, 0.26)
    defs.append(
        f'<linearGradient id="wash" x1="{corner[0]}" y1="{corner[1]}"'
        f' x2="{corner[2]}" y2="{corner[3]}">'
        f'<stop offset="0" stop-color="{_rgb(accent)}"'
        f' stop-opacity="{_n(wash_alpha)}"/>'
        f'<stop offset="0.55" stop-color="{_rgb(accent)}" stop-opacity="0.05"/>'
        f'<stop offset="1" stop-color="{_rgb(accent)}" stop-opacity="0"/>'
        "</linearGradient>"
    )
    body.append(f'<rect width="{W}" height="{H}" fill="url(#wash)"/>')

    # --- 3. aurora ellipses -------------------------------------------------
    # Radial gradients, which Pillow has no primitive for at all: the old path
    # drew flat white circles and blurred the entire overlay to fake this.
    for i in range(rng.randint(2, 4)):
        cx, cy = rng.uniform(-0.1, 1.1) * W, rng.uniform(-0.15, 1.15) * H
        rx = rng.uniform(0.18, 0.38) * W
        ry = rx * rng.uniform(0.45, 0.95)
        angle = rng.uniform(-40, 40)
        tint = haze if rng.random() < 0.6 else accent
        peak = rng.uniform(0.17, 0.30) * _soft_damp(cy)
        defs.append(
            f'<radialGradient id="a{i}" cx="0.5" cy="0.5" r="0.5">'
            f'<stop offset="0" stop-color="{_rgb(tint)}" stop-opacity="{_n(peak)}"/>'
            f'<stop offset="0.45" stop-color="{_rgb(tint)}"'
            f' stop-opacity="{_n(peak * 0.42)}"/>'
            f'<stop offset="1" stop-color="{_rgb(tint)}" stop-opacity="0"/>'
            "</radialGradient>"
        )
        body.append(
            f'<ellipse cx="{_n(cx)}" cy="{_n(cy)}" rx="{_n(rx)}" ry="{_n(ry)}"'
            f' transform="rotate({_n(angle)} {_n(cx)} {_n(cy)})"'
            f' fill="url(#a{i})"/>'
        )

    # --- 4. concentric rings, clipped to the frame -------------------------
    # Anchored off-canvas so only arcs of them cross the artwork. clipPath keeps
    # the geometry honest without computing the intersections by hand.
    defs.append(f'<clipPath id="frame"><rect width="{W}" height="{H}"/></clipPath>')
    ring_cx = rng.choice((-0.15, 1.15)) * W
    ring_cy = rng.uniform(-0.2, 1.2) * H
    rings: list[str] = []
    radius = rng.uniform(0.28, 0.42) * W
    for _ in range(rng.randint(4, 7)):
        alpha = rng.uniform(0.10, 0.19) * _soft_damp(ring_cy)
        rings.append(
            f'<circle cx="{_n(ring_cx)}" cy="{_n(ring_cy)}" r="{_n(radius)}"'
            f' fill="none" stroke="{_rgb(haze)}"'
            f' stroke-opacity="{_n(alpha)}"'
            f' stroke-width="{_n(rng.uniform(1.6, 4.0))}"/>'
        )
        radius += rng.uniform(52, 120)
    body.append(f'<g clip-path="url(#frame)">{"".join(rings)}</g>')

    # --- 5. long arcs -------------------------------------------------------
    arcs: list[str] = []
    for _ in range(rng.randint(5, 9)):
        y0 = rng.uniform(-0.05, 1.05) * H
        y1 = y0 + rng.uniform(-0.35, 0.35) * H
        ctrl_x = rng.uniform(0.2, 0.8) * W
        ctrl_y = (y0 + y1) / 2 + rng.uniform(-0.3, 0.3) * H
        alpha = rng.uniform(0.11, 0.24) * _soft_damp((y0 + y1) / 2)
        arcs.append(
            f'<path d="M -80 {_n(y0)} Q {_n(ctrl_x)} {_n(ctrl_y)}'
            f' {W + 80} {_n(y1)}" fill="none"'
            f' stroke="{_rgb(haze if rng.random() < 0.7 else accent)}"'
            f' stroke-opacity="{_n(alpha)}"'
            f' stroke-width="{_n(rng.uniform(1.4, 4.4))}"'
            ' stroke-linecap="round"/>'
        )
    body.append(f'<g clip-path="url(#frame)">{"".join(arcs)}</g>')

    # --- 6. dot scatter -----------------------------------------------------
    dots: list[str] = []
    for _ in range(rng.randint(16, 26)):
        cx, cy = rng.uniform(0, W), rng.uniform(0, H)
        dots.append(
            f'<circle cx="{_n(cx)}" cy="{_n(cy)}" r="{_n(rng.uniform(2.2, 5.4))}"'
            f' fill="{_rgb(haze)}"'
            f' fill-opacity="{_n(rng.uniform(0.16, 0.34) * _soft_damp(cy))}"/>'
        )
    body.append("".join(dots))

    # --- 7. scrim and vignette ---------------------------------------------
    # The scrim is the mechanical guarantee behind the WCAG test: whatever the
    # seeded composition does above, the band the h1 lands in is pulled down. It
    # is a soft four-stop ramp, so it reads as depth, not as a grey rectangle.
    defs.append(
        '<linearGradient id="scrim" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0.06" stop-color="#000" stop-opacity="0"/>'
        f'<stop offset="{_n(_TITLE_BAND[0])}" stop-color="#000" stop-opacity="0.20"/>'
        f'<stop offset="{_n(_TITLE_BAND[1])}" stop-color="#000" stop-opacity="0.20"/>'
        '<stop offset="0.96" stop-color="#000" stop-opacity="0"/>'
        "</linearGradient>"
    )
    body.append(f'<rect width="{W}" height="{H}" fill="url(#scrim)"/>')

    defs.append(
        '<radialGradient id="vignette" cx="0.5" cy="0.5" r="0.72">'
        '<stop offset="0.4" stop-color="#000" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#000" stop-opacity="0.28"/>'
        "</radialGradient>"
    )
    body.append(f'<rect width="{W}" height="{H}" fill="url(#vignette)"/>')

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"'
        f' viewBox="0 0 {W} {H}">\n'
        f'<defs>{"".join(defs)}</defs>\n'
        f'{"".join(body)}\n'
        "</svg>\n"
    )


def _rasterize_svg(svg: str, width: int, height: int) -> Image.Image:
    """Rasterise `svg` at an exact pixel size. Raises ImportError without cairosvg.

    The import is deliberately local rather than module-level: `cairosvg` is
    optional, and a module-level import would make the whole module — CLI,
    Pillow path and all — unimportable on a machine without libcairo.
    """
    import cairosvg  # noqa: PLC0415 -- optional dependency, checked per call

    png = cairosvg.svg2png(
        bytestring=svg.encode("utf-8"),
        output_width=width,
        output_height=height,
    )
    with Image.open(io.BytesIO(png)) as im:
        return im.convert("RGB")


# ---------------------------------------------------------------------------
# the Pillow renderer (fallback)
# ---------------------------------------------------------------------------


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


def render_pillow(category: str, seed: int) -> Image.Image:
    """The original Pillow composition: category gradient plus seeded pattern."""
    start, end = CATEGORY_COLORS[category]
    base = _gradient((BANNER_W, BANNER_H), start, end).convert("RGBA")
    overlay = _pattern_overlay((BANNER_W, BANNER_H), seed)
    return Image.alpha_composite(base, overlay).convert("RGB")


# ---------------------------------------------------------------------------
# the public entry point
# ---------------------------------------------------------------------------


def render_banner(title: str, category: str, out_dir: Path) -> tuple[Path, Path]:
    """Write banner.webp and teaser.webp into `out_dir`. Returns both paths.

    Pure artwork, no text: a category gradient plus a generative composition
    seeded from `category`, `title`, and `out_dir`'s name (the post slug in
    normal CLI use), so a rerun for the same post is byte-identical while
    different posts — even same-category, same-title-length posts — visibly
    differ.

    When `cairosvg` is importable the artwork is rendered from SVG and the
    vector source is written alongside as `banner.svg`. When it is not, the
    Pillow composition renders instead, a note goes to stderr, and any
    `banner.svg` left by an earlier SVG run is removed: that file is documented
    as the source of these rasters, and one that no longer matches them is worse
    than none.
    """
    if category not in CATEGORY_COLORS:
        raise ValueError(
            f"unknown category {category!r}; allowed: {sorted(CATEGORY_COLORS)}"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    slug = out_dir.name
    svg_path = out_dir / "banner.svg"

    svg = build_svg(title, category, slug)
    try:
        image = _rasterize_svg(svg, BANNER_W, BANNER_H)
        # Re-render the teaser from the vector source rather than downsampling
        # the banner: the gradients resolve at the target size instead of being
        # resampled, which is the point of keeping a vector master at all.
        teaser_image = _rasterize_svg(svg, TEASER_W, TEASER_H)
        svg_path.write_text(svg, encoding="utf-8")
    except ImportError as exc:
        print(
            f"make_banner: cairosvg unavailable ({exc}); "
            "falling back to the Pillow renderer. Install cairosvg (and libcairo) "
            "for the SVG banner and its editable banner.svg source.",
            file=sys.stderr,
        )
        image = render_pillow(category, _pattern_seed(category, title, slug))
        teaser_image = image.resize((TEASER_W, TEASER_H), Image.LANCZOS)
        svg_path.unlink(missing_ok=True)

    banner_path = out_dir / "banner.webp"
    image.save(banner_path, "WEBP", quality=Q_BANNER, method=6)

    teaser_path = out_dir / "teaser.webp"
    teaser_image.save(teaser_path, "WEBP", quality=Q_TEASER, method=6)

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
