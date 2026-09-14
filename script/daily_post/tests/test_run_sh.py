import fcntl
import os
import subprocess
from datetime import date
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
RUN_SH = REPO / "script" / "daily_post" / "run.sh"
TODAY = date.today().isoformat()


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "_posts").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "master"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "README.md").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
    return repo


@pytest.fixture
def stub_bin(tmp_path: Path) -> Path:
    """A PATH directory holding fake `gh` and `claude` executables."""
    d = tmp_path / "bin"
    d.mkdir()
    write_stub(d, "gh", "exit 0")
    write_stub(d, "claude", 'echo published > "$DAILY_POST_STATUS"; exit 0')
    return d


def write_stub(bin_dir: Path, name: str, body: str) -> None:
    path = bin_dir / name
    path.write_text(f"#!/usr/bin/env bash\n{body}\n", encoding="utf-8")
    path.chmod(0o755)


def run(repo: Path, stub_bin: Path, **env_extra) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "PATH": f"{stub_bin}:{os.environ['PATH']}",
        "DAILY_POST_REPO": str(repo),
        "DAILY_POST_SKIP_PULL": "1",
        **env_extra,
    }
    return subprocess.run(
        [str(RUN_SH)], capture_output=True, text=True, env=env
    )


def test_run_script_exists_and_is_executable():
    assert RUN_SH.is_file()
    assert RUN_SH.stat().st_mode & 0o111, "run.sh must be chmod +x"


def test_exit_0_when_the_skill_reports_published(fake_repo: Path, stub_bin: Path):
    result = run(fake_repo, stub_bin)
    assert result.returncode == 0, result.stdout + result.stderr


def test_exit_10_when_the_skill_reports_blocked(fake_repo: Path, stub_bin: Path):
    write_stub(stub_bin, "claude", 'echo blocked > "$DAILY_POST_STATUS"; exit 0')
    assert run(fake_repo, stub_bin).returncode == 10


def test_exit_20_when_the_skill_reports_no_topic(fake_repo: Path, stub_bin: Path):
    write_stub(stub_bin, "claude", 'echo no-topic > "$DAILY_POST_STATUS"; exit 0')
    assert run(fake_repo, stub_bin).returncode == 20


def test_exit_50_when_the_skill_writes_no_status(fake_repo: Path, stub_bin: Path):
    write_stub(stub_bin, "claude", "exit 0")
    assert run(fake_repo, stub_bin).returncode == 50


def test_exit_50_when_the_skill_reports_preflight_failed(fake_repo: Path, stub_bin: Path):
    write_stub(stub_bin, "claude", 'echo preflight-failed > "$DAILY_POST_STATUS"; exit 0')
    assert run(fake_repo, stub_bin).returncode == 50


def test_exit_30_when_a_post_for_today_already_exists(fake_repo: Path, stub_bin: Path):
    (fake_repo / "_posts" / f"{TODAY}-already-written.md").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=fake_repo, check=True)
    subprocess.run(["git", "commit", "-qm", "post"], cwd=fake_repo, check=True)
    result = run(fake_repo, stub_bin)
    assert result.returncode == 30
    assert "already" in (result.stdout + result.stderr).lower()


def test_exit_30_when_a_branch_for_today_already_exists(fake_repo: Path, stub_bin: Path):
    subprocess.run(
        ["git", "branch", f"daily-post/{TODAY}-something"], cwd=fake_repo, check=True
    )
    assert run(fake_repo, stub_bin).returncode == 30


def test_exit_40_when_gh_is_missing(fake_repo: Path, stub_bin: Path):
    """Relies on the real PATH having no `gh` — true on this machine.

    Do not override PATH to just `stub_bin`: that also hides `git`, and run.sh
    then fails on the git precondition instead of the gh one.
    """
    (stub_bin / "gh").unlink()
    result = run(fake_repo, stub_bin)
    assert result.returncode == 40
    assert "gh" in (result.stdout + result.stderr)


def test_exit_40_when_gh_is_not_authenticated(fake_repo: Path, stub_bin: Path):
    write_stub(stub_bin, "gh", "exit 1")
    result = run(fake_repo, stub_bin)
    assert result.returncode == 40
    assert "authenticate" in (result.stdout + result.stderr).lower()


def test_exit_40_when_the_working_tree_is_dirty(fake_repo: Path, stub_bin: Path):
    (fake_repo / "README.md").write_text("changed", encoding="utf-8")
    result = run(fake_repo, stub_bin)
    assert result.returncode == 40
    assert "clean" in (result.stdout + result.stderr).lower()


def test_the_run_is_logged(fake_repo: Path, stub_bin: Path):
    run(fake_repo, stub_bin)
    log = fake_repo / ".git" / "daily-post-logs" / f"{TODAY}.log"
    assert log.is_file()


def test_the_skill_is_invoked_with_the_daily_post_command(fake_repo: Path, stub_bin: Path):
    write_stub(
        stub_bin, "claude",
        'echo "$@" > "$DAILY_POST_REPO/args.txt"; echo published > "$DAILY_POST_STATUS"',
    )
    run(fake_repo, stub_bin)
    assert "/daily-post" in (fake_repo / "args.txt").read_text(encoding="utf-8")


def test_exit_40_when_the_repo_is_not_a_git_repository(tmp_path: Path, stub_bin: Path):
    """A precondition check must catch this before any expensive work — in
    particular `claude` must never be invoked."""
    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()
    write_stub(
        stub_bin, "claude",
        'touch "$DAILY_POST_REPO/claude-invoked.marker"; echo published > "$DAILY_POST_STATUS"',
    )
    result = run(not_a_repo, stub_bin)
    assert result.returncode == 40
    assert not (not_a_repo / "claude-invoked.marker").exists()


def test_exit_30_when_a_branch_for_today_exists_only_on_the_remote(
    fake_repo: Path, stub_bin: Path, tmp_path: Path
):
    """`git branch --list` is local-only; a branch pushed and then deleted
    locally (e.g. by a run on another machine) must still be detected via
    origin, or a second post gets written for the same day."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    subprocess.run(["git", "remote", "add", "origin", str(origin)], cwd=fake_repo, check=True)
    branch = f"daily-post/{TODAY}-something"
    subprocess.run(["git", "branch", branch], cwd=fake_repo, check=True)
    subprocess.run(["git", "push", "-q", "origin", branch], cwd=fake_repo, check=True)
    subprocess.run(["git", "branch", "-D", branch], cwd=fake_repo, check=True)

    result = run(fake_repo, stub_bin)
    assert result.returncode == 30


def test_a_remote_check_failure_does_not_abort_the_run(fake_repo: Path, stub_bin: Path, tmp_path: Path):
    """A flaky/unreachable origin for the remote-branch check must not kill an
    otherwise-healthy run: log a warning and keep going, using the local
    checks only."""
    dead_origin = tmp_path / "does-not-exist.git"
    subprocess.run(["git", "remote", "add", "origin", str(dead_origin)], cwd=fake_repo, check=True)

    result = run(fake_repo, stub_bin)
    assert result.returncode == 0, result.stdout + result.stderr


def test_a_concurrent_run_is_blocked_by_the_lock(fake_repo: Path, stub_bin: Path):
    """Two overlapping invocations (cron overlap, or a manual run on top of a
    scheduled one) must not both drive the pipeline in the same working
    directory."""
    write_stub(
        stub_bin, "claude",
        'touch "$DAILY_POST_REPO/claude-invoked.marker"; echo published > "$DAILY_POST_STATUS"',
    )
    lock_path = fake_repo / ".git" / "daily-post.lock"
    lock_file = open(lock_path, "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = run(fake_repo, stub_bin)
        assert result.returncode == 30
        assert not (fake_repo / "claude-invoked.marker").exists()
        assert "already" in (result.stdout + result.stderr).lower()
    finally:
        fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()
