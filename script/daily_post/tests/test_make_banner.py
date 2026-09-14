from pathlib import Path

import pytest
from PIL import Image

from script.daily_post.make_banner import (
    CATEGORY_COLORS,
    render_banner,
    resolve_font,
    wrap_title,
)
from script.daily_post.queue import CATEGORIES


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


def test_render_is_deterministic_for_the_same_input(tmp_path: Path):
    a, _ = render_banner("Same Title", "python", tmp_path / "a")
    b, _ = render_banner("Same Title", "python", tmp_path / "b")
    assert a.read_bytes() == b.read_bytes()


def test_a_very_long_title_still_renders(tmp_path: Path):
    title = "Why " + "extremely " * 20 + "long titles must not overflow the banner"
    banner, _ = render_banner(title, "infrastructure", tmp_path)
    assert banner.is_file()


def test_wrap_title_breaks_on_words_within_the_line_budget():
    font = resolve_font(80)
    lines = wrap_title("one two three four five six seven eight", font, max_width=400)
    assert len(lines) > 1
    assert all(line.strip() for line in lines)


def test_wrap_title_caps_the_line_count_and_ellipsises():
    font = resolve_font(80)
    lines = wrap_title(" ".join(["word"] * 60), font, max_width=400, max_lines=4)
    assert len(lines) == 4
    assert lines[-1].endswith("…")


def test_resolve_font_returns_a_usable_font():
    font = resolve_font(48)
    assert font.getbbox("Test") is not None
