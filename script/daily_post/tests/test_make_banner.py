from pathlib import Path

import pytest
from PIL import Image

from script.daily_post.make_banner import CATEGORY_COLORS, render_banner
from script.daily_post.queue import CATEGORIES


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    def chan(c: int) -> float:
        v = c / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def _contrast_ratio(rgb1: tuple[int, int, int], rgb2: tuple[int, int, int]) -> float:
    l1, l2 = _relative_luminance(rgb1), _relative_luminance(rgb2)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def test_every_category_has_a_gradient():
    assert set(CATEGORY_COLORS) == set(CATEGORIES)


def test_render_banner_writes_both_derivatives(tmp_path: Path):
    banner, teaser = render_banner("A Short Title", "python", tmp_path)
    assert banner.name == "banner.webp"
    assert teaser.name == "teaser.webp"
    assert banner.is_file() and teaser.is_file()


def test_banner_is_1600px_wide_webp(tmp_path: Path):
    banner, _ = render_banner("A Short Title", "python", tmp_path)
    with Image.open(banner) as im:
        assert im.width == 1600
        assert im.format == "WEBP"


def test_teaser_is_640px_wide_webp(tmp_path: Path):
    _, teaser = render_banner("A Short Title", "python", tmp_path)
    with Image.open(teaser) as im:
        assert im.width == 640
        assert im.format == "WEBP"


def test_render_banner_creates_a_missing_output_directory(tmp_path: Path):
    out = tmp_path / "assets" / "images" / "some-slug"
    banner, _ = render_banner("Title", "databases", out)
    assert banner.parent == out


def test_render_banner_rejects_an_unknown_category(tmp_path: Path):
    with pytest.raises(ValueError, match="knitting"):
        render_banner("Title", "knitting", tmp_path)


def test_different_categories_produce_different_images(tmp_path: Path):
    a, _ = render_banner("Same Title", "python", tmp_path / "a")
    b, _ = render_banner("Same Title", "databases", tmp_path / "b")
    assert a.read_bytes() != b.read_bytes()


def test_same_category_different_slugs_produce_different_images(tmp_path: Path):
    """Per-post variation: same title, same category, different slug (the leaf
    directory name, which is what the CLI derives from --slug) must not collide."""
    a, _ = render_banner("Same Title", "python", tmp_path / "post-one")
    b, _ = render_banner("Same Title", "python", tmp_path / "post-two")
    assert a.read_bytes() != b.read_bytes()


def test_same_slug_renders_deterministically_twice(tmp_path: Path):
    """Same title, category, and slug (leaf directory name) -> byte-identical
    output, even across separate invocations writing into different parents."""
    a, _ = render_banner("Same Title", "python", tmp_path / "run1" / "my-post")
    b, _ = render_banner("Same Title", "python", tmp_path / "run2" / "my-post")
    assert a.read_bytes() == b.read_bytes()


def test_a_very_long_title_still_renders(tmp_path: Path):
    title = "Why " + "extremely " * 20 + "long titles must not overflow the banner"
    banner, _ = render_banner(title, "infrastructure", tmp_path)
    assert banner.is_file()


def test_banner_contains_no_baked_in_text(tmp_path: Path):
    """The theme paints the h1/lead/meta on top of header.overlay_image itself
    (see _layouts/single.html -> page__hero), so a banner with its own title text
    would show the title twice. The banner must be pure artwork: a solid-colour
    background must differ from ours (i.e. we drew *something*), but nothing
    resembling glyph strokes -- checked indirectly via the pattern/contrast tests
    below, since OCR isn't available here. This test only pins the *contract*:
    render_banner takes no text-layout knobs any more.
    """
    import inspect

    from script.daily_post import make_banner

    assert not hasattr(make_banner, "wrap_title")
    assert not hasattr(make_banner, "resolve_font")
    sig = inspect.signature(render_banner)
    assert list(sig.parameters) == ["title", "category", "out_dir"]


@pytest.mark.parametrize("category", sorted(CATEGORY_COLORS))
def test_darkened_banner_clears_wcag_aa_in_the_title_zone(tmp_path: Path, category: str):
    """Simulate the theme's `overlay_filter: 0.5` (a 50% black layer) and confirm
    white text would still read at WCAG AA (>= 4.5:1) against the busiest plausible
    pixel in the zone where page__title/page__lead actually render: the vertical
    middle band, left-aligned within the page's centered content wrapper.

    Uses per-channel extrema (the brightest R, the brightest G, the brightest B
    anywhere in the zone, combined into one hypothetical pixel) as a conservative
    upper bound on brightness, rather than sampling -- this can only overstate the
    true worst pixel's luminance, never understate it, so a pass here is safe.

    Parametrized over every category in CATEGORY_COLORS: a gradient change to any
    one category's end colour must not silently drop it below the WCAG AA floor for
    the white title the theme paints on top.
    """
    banner, _ = render_banner(
        "Postgres connection pooling under sustained load", category, tmp_path
    )
    with Image.open(banner) as im:
        w, h = im.size
        zone = im.convert("RGB").crop(
            (0, round(h * 0.22), round(w * 0.78), round(h * 0.78))
        )
        r, g, b = zone.split()
        worst_bright_pixel = (r.getextrema()[1], g.getextrema()[1], b.getextrema()[1])

    darkened = tuple(round(c * 0.5) for c in worst_bright_pixel)
    contrast = _contrast_ratio((255, 255, 255), darkened)
    assert contrast >= 4.5, (
        f"worst-case pixel {worst_bright_pixel} darkened to {darkened} only "
        f"gives {contrast:.2f}:1 contrast against white text"
    )


# ---------------------------------------------------------------------------
# the SVG renderer, and the Pillow fallback behind it
# ---------------------------------------------------------------------------
#
# `cairosvg` is optional (see script/daily_post/README.md): the SVG-specific
# tests skip without it, while every contract test above keeps running against
# whichever renderer is actually available on this machine.

import sys
import xml.etree.ElementTree as ET

from script.daily_post.make_banner import (
    BANNER_H,
    BANNER_W,
    TEASER_H,
    TEASER_W,
    build_svg,
)

SVG_NS = "{http://www.w3.org/2000/svg}"

try:
    import cairosvg  # noqa: F401

    HAVE_CAIROSVG = True
except ImportError:  # pragma: no cover - depends on the machine
    HAVE_CAIROSVG = False

needs_cairosvg = pytest.mark.skipif(
    not HAVE_CAIROSVG, reason="cairosvg is not installed; the Pillow path is in use"
)


@pytest.fixture
def no_cairosvg(monkeypatch):
    """Simulate a machine without libcairo.

    `None` in `sys.modules` is exactly what CPython leaves behind for a module
    that cannot be imported, and `import cairosvg` against it raises ImportError
    - the same exception `render_banner` catches in production. Patching the
    import itself, rather than the renderer, keeps the test honest about *where*
    the failure happens.
    """
    monkeypatch.setitem(sys.modules, "cairosvg", None)


# --- the SVG source ---------------------------------------------------------


def test_build_svg_produces_well_formed_xml():
    root = ET.fromstring(build_svg("Some Title", "python", "my-post"))
    assert root.tag == f"{SVG_NS}svg"
    assert root.get("viewBox") == f"0 0 {BANNER_W} {BANNER_H}"


def test_build_svg_contains_no_lettering():
    """Same rule as the raster: the theme paints the h1 on top of this image, so
    any glyph in the artwork would render the title twice."""
    root = ET.fromstring(build_svg("Some Title", "databases", "my-post"))
    for tag in ("text", "tspan", "textPath", "image", "foreignObject"):
        assert root.find(f".//{SVG_NS}{tag}") is None, f"the SVG contains a <{tag}>"


def test_build_svg_uses_the_svg_primitives_pillow_lacks():
    """A port that only redrew the old Pillow composition in SVG would be effort
    spent for no gain. Pin the primitives that are the reason for the rewrite."""
    svg = build_svg("Some Title", "web-development", "my-post")
    for primitive in ("radialGradient", "linearGradient", "clipPath", "stroke-width"):
        assert primitive in svg, f"the SVG never uses {primitive}"


def test_build_svg_is_deterministic():
    a = build_svg("Same Title", "python", "my-post")
    b = build_svg("Same Title", "python", "my-post")
    assert a == b


def test_build_svg_varies_by_slug():
    a = build_svg("Same Title", "python", "post-one")
    b = build_svg("Same Title", "python", "post-two")
    assert a != b


def test_build_svg_varies_by_category():
    a = build_svg("Same Title", "python", "my-post")
    b = build_svg("Same Title", "databases", "my-post")
    assert a != b


def test_build_svg_rejects_an_unknown_category():
    with pytest.raises(ValueError, match="knitting"):
        build_svg("Title", "knitting", "my-post")


@needs_cairosvg
def test_the_svg_source_ships_next_to_the_rasters(tmp_path: Path):
    """The "attach the vector to the post" half of the contract: the editable
    source lives in the same assets directory as the WebP files it produced."""
    banner, _ = render_banner("A Short Title", "python", tmp_path)
    svg = banner.parent / "banner.svg"
    assert svg.is_file()
    assert ET.fromstring(svg.read_text(encoding="utf-8")).tag == f"{SVG_NS}svg"


@needs_cairosvg
def test_the_shipped_svg_is_the_one_the_rasters_came_from(tmp_path: Path):
    banner, _ = render_banner("A Short Title", "python", tmp_path / "my-post")
    written = (banner.parent / "banner.svg").read_text(encoding="utf-8")
    assert written == build_svg("A Short Title", "python", "my-post")


@needs_cairosvg
def test_the_svg_path_writes_webp_at_both_sizes(tmp_path: Path):
    banner, teaser = render_banner("A Short Title", "databases", tmp_path)
    with Image.open(banner) as im:
        assert (im.format, im.size) == ("WEBP", (BANNER_W, BANNER_H))
    with Image.open(teaser) as im:
        assert (im.format, im.size) == ("WEBP", (TEASER_W, TEASER_H))


# --- the Pillow fallback ----------------------------------------------------


def test_the_fallback_renders_when_cairosvg_cannot_be_imported(
    tmp_path: Path, no_cairosvg, capsys
):
    """A cron box without libcairo must still get a banner. Losing the artwork
    is a bad day; failing the whole run over it is a worse one."""
    banner, teaser = render_banner("A Short Title", "python", tmp_path)
    with Image.open(banner) as im:
        assert (im.format, im.size) == ("WEBP", (BANNER_W, BANNER_H))
    with Image.open(teaser) as im:
        assert (im.format, im.size) == ("WEBP", (TEASER_W, TEASER_H))
    assert "cairosvg unavailable" in capsys.readouterr().err


def test_the_fallback_does_not_claim_an_svg_source_it_did_not_use(
    tmp_path: Path, no_cairosvg
):
    render_banner("A Short Title", "python", tmp_path)
    assert not (tmp_path / "banner.svg").exists()


def test_the_fallback_clears_a_stale_svg_from_an_earlier_run(
    tmp_path: Path, no_cairosvg
):
    """banner.svg is documented as the source of these rasters. One left behind
    by a run on a machine that *had* cairosvg no longer describes them, and a
    wrong source file is worse than no source file."""
    (tmp_path / "banner.svg").write_text("<svg/>", encoding="utf-8")
    render_banner("A Short Title", "python", tmp_path)
    assert not (tmp_path / "banner.svg").exists()


def test_the_fallback_is_deterministic(tmp_path: Path, no_cairosvg):
    a, _ = render_banner("Same Title", "python", tmp_path / "run1" / "my-post")
    b, _ = render_banner("Same Title", "python", tmp_path / "run2" / "my-post")
    assert a.read_bytes() == b.read_bytes()


def test_the_fallback_varies_by_slug(tmp_path: Path, no_cairosvg):
    a, _ = render_banner("Same Title", "python", tmp_path / "post-one")
    b, _ = render_banner("Same Title", "python", tmp_path / "post-two")
    assert a.read_bytes() != b.read_bytes()


@pytest.mark.parametrize("category", sorted(CATEGORY_COLORS))
def test_the_fallback_also_clears_wcag_aa_in_the_title_zone(
    tmp_path: Path, category: str, no_cairosvg
):
    """The legibility floor is a property of the banner, not of whichever
    renderer happened to draw it. The parametrized test above covers the
    renderer this machine actually uses; this one covers the fallback
    unconditionally, so a developer with cairosvg installed cannot leave the
    cron path unchecked.
    """
    banner, _ = render_banner(
        "Postgres connection pooling under sustained load", category, tmp_path
    )
    with Image.open(banner) as im:
        w, h = im.size
        zone = im.convert("RGB").crop(
            (0, round(h * 0.22), round(w * 0.78), round(h * 0.78))
        )
        r, g, b = zone.split()
        worst_bright_pixel = (r.getextrema()[1], g.getextrema()[1], b.getextrema()[1])

    darkened = tuple(round(c * 0.5) for c in worst_bright_pixel)
    contrast = _contrast_ratio((255, 255, 255), darkened)
    assert contrast >= 4.5, (
        f"worst-case pixel {worst_bright_pixel} darkened to {darkened} only "
        f"gives {contrast:.2f}:1 contrast against white text"
    )
