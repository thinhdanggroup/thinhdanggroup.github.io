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
