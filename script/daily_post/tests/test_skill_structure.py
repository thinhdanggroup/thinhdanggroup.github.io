import re
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


SKILL_MD = SKILL_DIR / "SKILL.md"

STATUS_TOKENS = ("published", "blocked", "no-topic", "preflight-failed")


def test_skill_md_exists():
    assert SKILL_MD.is_file()


def test_skill_md_has_name_and_description_front_matter():
    import yaml

    text = SKILL_MD.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    fm = yaml.safe_load(text.split("---\n")[1])
    assert fm["name"] == "daily-post"
    assert len(fm["description"]) > 40


def test_skill_md_links_every_reference_file():
    text = SKILL_MD.read_text(encoding="utf-8")
    for name in REFERENCE_FILES:
        assert f"references/{name}" in text, f"SKILL.md never references {name}"


def test_skill_md_names_every_script_it_drives():
    text = SKILL_MD.read_text(encoding="utf-8")
    for script in ("dupe_check.py", "make_banner.py", "preflight.sh", "queue.py"):
        assert script in text, f"SKILL.md never invokes {script}"


@pytest.mark.parametrize("token", STATUS_TOKENS)
def test_skill_md_documents_every_status_token(token: str):
    assert token in SKILL_MD.read_text(encoding="utf-8")


def test_skill_md_writes_to_the_status_file_variable():
    assert "DAILY_POST_STATUS" in SKILL_MD.read_text(encoding="utf-8")


def test_skill_md_forbids_interactive_prompts():
    """The pipeline runs unattended; a question is a hang, not a pause."""
    text = SKILL_MD.read_text(encoding="utf-8").lower()
    assert "never ask" in text or "no questions" in text


def test_skill_md_states_the_revision_cap():
    text = SKILL_MD.read_text(encoding="utf-8")
    assert "two revision" in text.lower() or "2 revision" in text.lower()


def test_skill_md_returns_to_clean_master():
    """Every terminal path must leave the checkout on master, branch cleaned up.

    Regression guard for Task 9 fix round 1, Finding 1 (critical): a run that
    stops on a feature branch silently breaks the next day's run.
    """
    text = SKILL_MD.read_text(encoding="utf-8")
    assert "git checkout master" in text
    assert "git branch -D" in text


def test_skill_md_defines_concrete_scratch_path():
    """`research.md` must live at a resolved path, not just 'the scratch directory'.

    Regression guard for Task 9 fix round 1, Finding 2: gate subagents cannot find
    an unresolved path.
    """
    assert "daily-post-scratch" in SKILL_MD.read_text(encoding="utf-8")


def test_skill_md_marks_duplicate_queue_topics_rejected():
    """A duplicate that came from the queue must be marked `rejected`, in Stage 1.

    Regression guard for Task 9 fix round 1, Finding 3: otherwise `next_queued()`
    hands back the same known-duplicate topic on every future run.
    """
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.index("## Stage 1")
    end = text.index("## Stage 2")
    stage_one = text[start:end]
    assert "rejected" in stage_one


def test_skill_md_states_queue_state_lives_on_master():
    """SKILL.md must state the rule that queue bookkeeping is committed to
    master directly, never left stranded on an unmerged feature branch.

    Regression guard for Task 9 fix round 2, Finding 4: a claim that only ever
    lands on the feature branch leaves master reading `queued`, so tomorrow's
    run picks the same topic again while today's PR is still open.
    """
    text = SKILL_MD.read_text(encoding="utf-8")
    assert "Queue state is pipeline bookkeeping and lives on" in text


def test_skill_md_feature_branch_never_stages_the_queue_file():
    """No `git checkout -b "daily-post/...` code block may also stage
    `_data/topic_queue.yml` — that file's state must be committed straight to
    master, never bundled into the feature branch alongside the post.

    Regression guard for Task 9 fix round 2, Finding 4: bundling the queue
    mutation into the feature-branch commit is exactly what let a claim sit
    unmerged on a branch while master kept reading the topic as `queued`.
    """
    text = SKILL_MD.read_text(encoding="utf-8")
    branch_blocks = re.findall(r"```bash\n(.*?)```", text, re.DOTALL)
    branch_blocks = [b for b in branch_blocks if 'git checkout -b "daily-post/' in b]
    assert branch_blocks, "no feature-branch code block found to check"
    for block in branch_blocks:
        assert "topic_queue.yml" not in block, (
            "a feature-branch code block still stages topic_queue.yml:\n" + block
        )
