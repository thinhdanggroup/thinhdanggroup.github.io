from pathlib import Path

import pytest

from script.daily_post.queue import CATEGORIES

REPO = Path(__file__).resolve().parents[3]
SKILL_DIR = REPO / ".claude" / "skills" / "daily-post"
REFS = SKILL_DIR / "references"

REFERENCE_FILES = ("frontmatter.md", "voice.md", "sources.md", "gates.md")


@pytest.mark.parametrize("name", REFERENCE_FILES)
def test_reference_file_exists_and_is_not_a_stub(name: str):
    path = REFS / name
    assert path.is_file(), f"missing reference file: {name}"
    assert len(path.read_text(encoding="utf-8")) > 500, f"{name} looks like a stub"


def test_frontmatter_reference_lists_every_category():
    text = (REFS / "frontmatter.md").read_text(encoding="utf-8")
    for category in CATEGORIES:
        assert category in text, f"frontmatter.md does not mention {category}"


def test_frontmatter_reference_states_the_description_bounds():
    text = (REFS / "frontmatter.md").read_text(encoding="utf-8")
    assert "50" in text and "200" in text


def test_gates_reference_names_all_four_gates():
    text = (REFS / "gates.md").read_text(encoding="utf-8").lower()
    for gate in ("fact", "duplicate", "code", "voice"):
        assert gate in text, f"gates.md does not define the {gate} gate"


def test_gates_reference_states_the_revision_cap():
    text = (REFS / "gates.md").read_text(encoding="utf-8").lower()
    assert "at most two revision rounds" in text


@pytest.mark.parametrize("name", REFERENCE_FILES)
def test_reference_files_contain_no_placeholders(name: str):
    text = (REFS / name).read_text(encoding="utf-8")
    for marker in ("TODO", "TBD", "FIXME", "XXX"):
        assert marker not in text, f"{name} still contains {marker}"
