import json
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]


def test_makefile_exposes_the_daily_post_targets():
    text = (REPO / "Makefile").read_text(encoding="utf-8")
    for target in ("daily-post:", "daily-post-test:", "daily-post-preflight:"):
        assert target in text, f"Makefile is missing the {target} target"


def test_readme_documents_the_pipeline():
    text = (REPO / "README.md").read_text(encoding="utf-8")
    assert "Daily post pipeline" in text
    assert "script/daily_post/run.sh" in text
    assert "_data/topic_queue.yml" in text


def test_readme_documents_every_exit_code():
    text = (REPO / "README.md").read_text(encoding="utf-8")
    for code in ("0", "10", "20", "30", "40", "50"):
        assert f"`{code}`" in text, f"README does not document exit code {code}"


def test_docs_are_excluded_from_the_jekyll_build():
    """Either spelling counts.

    Jekyll's exclude matcher delegates to Ruby's `File.join`, so `/docs` already
    excludes the same tree that `docs` does — listing both is redundant, and a
    test that insists on one exact spelling pins that redundancy in place. What
    matters is that the tree is excluded, not how it is written.
    """
    config = yaml.safe_load((REPO / "_config.yml").read_text(encoding="utf-8"))
    excluded = set(config["exclude"])
    assert excluded & {"docs", "/docs", "docs/"}, (
        "_config.yml no longer excludes the docs tree from the Jekyll build"
    )


def test_script_readme_exists():
    assert (REPO / "script" / "daily_post" / "README.md").is_file()


def test_readme_documents_the_new_exit_codes():
    text = (REPO / "README.md").read_text(encoding="utf-8")
    for code in ("31", "60", "70"):
        assert f"`{code}`" in text, f"README does not document exit code {code}"


def test_readme_says_the_pipeline_pushes_to_master():
    """I4: the owner of a repo serving a live site must be told, in the README,
    that an unattended pipeline pushes to master — and exactly what it pushes.
    """
    text = (REPO / "README.md").read_text(encoding="utf-8")
    assert "pushes to `master` directly" in text
    assert "No post content ever reaches `master`" in text


def test_headless_permissions_are_configured():
    """C3: `claude -p` cannot answer a permission prompt, so a repo shipping no
    permission configuration fails every tool call that needs approval — which
    pushes an operator toward a blanket bypass.
    """
    settings = REPO / ".claude" / "settings.json"
    assert settings.is_file(), ".claude/settings.json is missing"
    config = json.loads(settings.read_text(encoding="utf-8"))
    allow = config["permissions"]["allow"]
    assert allow, "the allowlist is empty"
    joined = " ".join(allow)
    for needed in ("git ", "gh ", "script/daily_post", "preflight.sh", "WebSearch"):
        assert needed in joined, f"the allowlist covers no {needed!r} usage"


def test_no_permission_bypass_anywhere_in_the_pipeline():
    """C3: an explicit allowlist exists so nobody reaches for the bypass. The
    bypass must not appear in the scripts, the skill, or the docs that tell an
    operator what to run.
    """
    for path in (
        REPO / "script" / "daily_post" / "run.sh",
        REPO / "script" / "daily_post" / "README.md",
        REPO / "README.md",
        REPO / ".claude" / "settings.json",
        REPO / ".claude" / "skills" / "daily-post" / "SKILL.md",
        REPO / "Makefile",
    ):
        text = path.read_text(encoding="utf-8")
        occurrences = text.count("--dangerously-skip-permissions")
        if path.name == "README.md":
            # A README may name it once, and only to tell the operator not to
            # use it — the allowlist exists precisely so nobody needs to.
            assert occurrences <= 1, f"{path} mentions the bypass more than once"
            if occurrences:
                where = text.index("--dangerously-skip-permissions")
                context = text[max(0, where - 200):where + 120].lower()
                assert "do not" in context or "no `--dangerously" in context, (
                    f"{path} names the bypass without forbidding it"
                )
            continue
        assert occurrences == 0, f"{path} references --dangerously-skip-permissions"
