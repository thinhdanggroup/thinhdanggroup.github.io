import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
PREFLIGHT = REPO / "script" / "daily_post" / "preflight.sh"


def run_preflight(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(PREFLIGHT), *args], cwd=REPO, capture_output=True, text=True
    )


def test_preflight_script_exists_and_is_executable():
    assert PREFLIGHT.is_file()
    assert PREFLIGHT.stat().st_mode & 0o111, "preflight.sh must be chmod +x"


def test_fast_mode_passes_on_the_clean_repo():
    result = run_preflight("--fast")
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.fixture
def broken_post():
    """Writes into the REAL `_posts/` directory (an isolated `tmp_path` cannot be
    used here: `script/check_frontmatter.py` hardcodes `POSTS = REPO / "_posts"`
    with no override flag). Registering teardown before the file is ever created
    means it is removed whether the test passes, fails, or raises — including an
    interrupt, which would otherwise strand this file in the repo and break
    check_frontmatter.py, preflight, CI, and the daily pipeline until someone
    deletes it by hand.
    """
    path = REPO / "_posts" / "2099-01-01-preflight-self-test.md"
    yield path
    path.unlink(missing_ok=True)


def test_fast_mode_fails_on_a_post_that_breaks_the_contract(broken_post: Path):
    """A post with no description must make preflight red."""
    broken_post.write_text(
        '---\ntitle: "Preflight self test"\ntags:\n    - Python\n'
        "categories:\n    - python\n---\n\nBody.\n",
        encoding="utf-8",
    )
    result = run_preflight("--fast")
    assert result.returncode != 0
    assert "description" in (result.stdout + result.stderr)


@pytest.mark.slow
def test_full_preflight_builds_the_site():
    if shutil.which("bundle") is None:
        pytest.skip("bundler not installed")
    result = run_preflight()
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-4000:]
