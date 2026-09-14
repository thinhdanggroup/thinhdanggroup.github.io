import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
PREFLIGHT = REPO / "script" / "daily_post" / "preflight.sh"

GREEN = 0
RED = 1          # a check ran and failed: the post is implicated
ENVIRONMENT = 2  # the checks could not run at all: the post says nothing


def run_preflight(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(PREFLIGHT), *args], cwd=REPO, capture_output=True, text=True, env=env
    )


def make_bindir(root: Path, name: str, *tools: str) -> Path:
    """A PATH directory holding exactly the named tools (plus the shell itself).

    `bash` is always present because preflight.sh is a bash script — a PATH
    without it never reaches the script's own logic at all.
    """
    bindir = root / name
    bindir.mkdir()
    for tool in ("bash", *tools):
        real = shutil.which(tool)
        assert real, f"{tool} must exist to build a test PATH"
        (bindir / tool).symlink_to(real)
    return bindir


@pytest.fixture
def bin_without_bundler(tmp_path: Path) -> Path:
    """A PATH with python3 but no bundler.

    Simulates the real cron failure mode: bundler is installed into the user gem
    directory, which an interactive shell has on PATH and a scheduler does not.
    """
    bindir = make_bindir(tmp_path, "bin")
    (bindir / "python3").symlink_to(sys.executable)
    return bindir


def env_with_path(bindir: Path) -> dict:
    env = dict(os.environ)
    env["PATH"] = str(bindir)
    return env


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
    assert result.returncode == RED, (
        "a post that breaks the contract must exit 1 (RED), not 2 (ENVIRONMENT): "
        "exit 2 tells the skill to preserve the draft, which would be wrong here"
    )
    assert "description" in (result.stdout + result.stderr)


@pytest.mark.slow
def test_full_preflight_builds_the_site():
    if shutil.which("bundle") is None:
        pytest.skip("bundler not installed")
    result = run_preflight()
    assert result.returncode == GREEN, result.stdout[-4000:] + result.stderr[-4000:]


def test_missing_bundler_is_an_environment_failure_not_a_red_post(
    bin_without_bundler: Path,
):
    """Exit 2, never exit 1.

    Regression guard for the first real run: SKILL.md Stage 5 reads exit 1 as
    "this run produced a broken post" and reverts the topic to `queued` while
    moving the draft aside. A bundler that is merely off PATH — exactly what
    happens under cron — would therefore have silently discarded a good,
    finished post. Exit 2 says "the environment cannot run the checks", and the
    post is left alone.
    """
    result = run_preflight(env=env_with_path(bin_without_bundler))
    output = result.stdout + result.stderr
    assert result.returncode == ENVIRONMENT, (
        f"expected {ENVIRONMENT} (environment), got {result.returncode}\n" + output
    )
    assert "ENVIRONMENT PROBLEM" in output
    assert "bundle" in output
    assert "says nothing about the post" in output


def test_unrunnable_bundle_exec_jekyll_is_an_environment_failure(
    bin_without_bundler: Path,
):
    """Bundler present but the bundle broken is still the environment's fault."""
    stub = bin_without_bundler / "bundle"
    stub.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
    stub.chmod(0o755)

    result = run_preflight(env=env_with_path(bin_without_bundler))
    output = result.stdout + result.stderr
    assert result.returncode == ENVIRONMENT, (
        f"expected {ENVIRONMENT} (environment), got {result.returncode}\n" + output
    )
    assert "ENVIRONMENT PROBLEM" in output
    assert "jekyll" in output


def test_missing_python3_is_an_environment_failure(tmp_path: Path):
    """The front matter check is python3; without it nothing was checked."""
    no_python = make_bindir(tmp_path, "no-python-bin")
    result = run_preflight("--fast", env=env_with_path(no_python))
    output = result.stdout + result.stderr
    assert result.returncode == ENVIRONMENT, (
        f"expected {ENVIRONMENT} (environment), got {result.returncode}\n" + output
    )
    assert "ENVIRONMENT PROBLEM" in output


def test_header_documents_all_three_exit_codes():
    """The script's own header is where an operator reads the contract."""
    header = PREFLIGHT.read_text(encoding="utf-8").split("set -", 1)[0]
    assert "GREEN" in header
    assert "RED" in header
    assert "ENVIRONMENT" in header
    for code in ("0", "1", "2"):
        assert code in header

