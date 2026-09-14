import fcntl
import os
import shutil
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


@pytest.fixture
def path_without_gh(tmp_path: Path) -> Path:
    """A PATH directory mirroring the real PATH with `gh` removed.

    This test used to rely on the machine's real PATH simply having no `gh`,
    which is a fact about one laptop rather than about run.sh: it started
    failing the moment `gh` was installed — and `gh` is a prerequisite of the
    very pipeline under test, so installing it is the expected state. Mirroring
    the PATH keeps `git`, `python3`, `flock` and `timeout` reachable (dropping
    them would make run.sh die on a *different* precondition and pass this test
    for the wrong reason) while making `gh` genuinely absent.
    """
    shim = tmp_path / "path-without-gh"
    shim.mkdir()
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if not directory or not os.path.isdir(directory):
            continue
        for entry in os.scandir(directory):
            link = shim / entry.name
            if entry.name == "gh" or os.path.lexists(link):
                continue
            try:
                link.symlink_to(entry.path)
            except OSError:
                pass
    assert not os.path.lexists(shim / "gh")
    return shim


def test_exit_40_when_gh_is_missing(
    fake_repo: Path, stub_bin: Path, path_without_gh: Path
):
    """run.sh must hard-fail with 40 when `gh` cannot be found.

    Do not override PATH to just `stub_bin`: that also hides `git`, and run.sh
    then fails on the git precondition instead of the gh one.
    """
    (stub_bin / "gh").unlink()
    result = run(fake_repo, stub_bin, PATH=f"{stub_bin}{os.pathsep}{path_without_gh}")
    assert result.returncode == 40, result.stdout + result.stderr
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


def test_a_remote_warning_on_stderr_is_not_read_as_an_existing_branch(
    fake_repo: Path, stub_bin: Path, tmp_path: Path
):
    """`git ls-remote` can exit 0 with empty stdout while writing a warning to
    stderr — ssh's "Permanently added ... to the list of known hosts" is the
    common one, and it recurs on *every* connection wherever
    UserKnownHostsFile is /dev/null. Captured with 2>&1, that warning reads as
    a branch listing, so every run reports "already ran today" and exits 30
    forever: the pipeline stops dead behind the one code operators are
    explicitly told to ignore."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    subprocess.run(["git", "remote", "add", "origin", str(origin)], cwd=fake_repo, check=True)
    real_git = shutil.which("git")
    write_stub(
        stub_bin,
        "git",
        'if [[ "$1" == "ls-remote" ]]; then\n'
        '  echo "Warning: Permanently added \'github.com\' (ED25519) to the'
        ' list of known hosts." >&2\n'
        'fi\n'
        f'exec {real_git} "$@"',
    )

    result = run(fake_repo, stub_bin)
    assert result.returncode == 0, result.stdout + result.stderr


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
    directory. This pins the genuinely-held-lock case (exit 31) apart from
    the lock-acquisition-FAILURE case (exit 40, see the test below).

    Final-review fix I1: this used to exit 30, the same code as "already ran
    today" — which the README tells operators to ignore. A hung run holds the
    lock forever, so every later run exited 30 and the pipeline stopped
    producing posts while reporting the all-clear. 31 makes a stuck lock
    visible from the exit code alone."""
    write_stub(
        stub_bin, "claude",
        'touch "$DAILY_POST_REPO/claude-invoked.marker"; echo published > "$DAILY_POST_STATUS"',
    )
    lock_path = fake_repo / ".git" / "daily-post.lock"
    lock_file = open(lock_path, "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = run(fake_repo, stub_bin)
        assert result.returncode == 31, result.stdout + result.stderr
        assert not (fake_repo / "claude-invoked.marker").exists()
        assert "lock" in (result.stdout + result.stderr).lower()
    finally:
        fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores permission bits")
def test_exit_40_when_the_lock_file_cannot_be_opened(fake_repo: Path, stub_bin: Path):
    """A lock-acquisition FAILURE (permission denied, disk full, fd
    exhaustion) is a real environment problem, not "another run is already in
    progress" — it must surface as a precondition failure (40), not be
    swallowed into the benign "nothing to do" code (30) that operators are
    told to ignore. Simulated here by making `.git` unwritable so
    `exec 9>.git/daily-post.lock` cannot create the lock file.

    Skipped under a root-run CI: root ignores permission bits, so the
    unwritable-directory condition cannot be reproduced and this test would
    otherwise fail rather than silently pass. Failing loudly is better than a
    false green, so this guard is a portability fix, not a correctness one.
    """
    write_stub(
        stub_bin, "claude",
        'touch "$DAILY_POST_REPO/claude-invoked.marker"; echo published > "$DAILY_POST_STATUS"',
    )
    git_dir = fake_repo / ".git"
    original_mode = git_dir.stat().st_mode
    git_dir.chmod(0o555)
    try:
        result = run(fake_repo, stub_bin)
        assert result.returncode == 40, result.stdout + result.stderr
        assert not (fake_repo / "claude-invoked.marker").exists()
    finally:
        # Restore write permission so pytest can clean up tmp_path afterward.
        git_dir.chmod(original_mode)


# --- final-review regression guards -----------------------------------------


def test_exit_40_when_master_is_not_checked_out(fake_repo: Path, stub_bin: Path):
    """I2: nothing verified which branch was checked out.

    On a feature branch, `git pull --ff-only origin master` fast-forwards the
    wrong ref and every later `git push origin master` pushes that ref instead,
    silently orphaning the queue commits. The skill must never be invoked in
    that state.
    """
    write_stub(
        stub_bin, "claude",
        'touch "$DAILY_POST_REPO/claude-invoked.marker"; echo published > "$DAILY_POST_STATUS"',
    )
    subprocess.run(["git", "checkout", "-q", "-b", "some-feature"], cwd=fake_repo, check=True)
    result = run(fake_repo, stub_bin)
    assert result.returncode == 40, result.stdout + result.stderr
    output = result.stdout + result.stderr
    assert "master" in output and "some-feature" in output
    assert not (fake_repo / "claude-invoked.marker").exists()


def test_exit_30_for_already_ran_today_is_distinct_from_the_lock_code(
    fake_repo: Path, stub_bin: Path
):
    """I1: "already ran today" and "the lock is held" must not share a code.

    30 is the code operators are told to ignore; a held lock is how a hung run
    silently stops the pipeline, so the two have to be distinguishable without
    reading the log.
    """
    (fake_repo / "_posts" / f"{TODAY}-already-written.md").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=fake_repo, check=True)
    subprocess.run(["git", "commit", "-qm", "post"], cwd=fake_repo, check=True)
    assert run(fake_repo, stub_bin).returncode == 30


def test_exit_60_when_the_skill_exceeds_the_timeout(fake_repo: Path, stub_bin: Path):
    """I1: an unbounded `claude` call can hang forever holding the lock.

    The killed run must report a code of its own — never 30, and never 0 via a
    status file some earlier run left behind.
    """
    write_stub(stub_bin, "claude", "sleep 30")
    result = run(fake_repo, stub_bin, DAILY_POST_TIMEOUT="1")
    assert result.returncode == 60, result.stdout + result.stderr
    assert "timed out" in (result.stdout + result.stderr).lower()


def test_git_cannot_block_on_an_interactive_prompt(fake_repo: Path, stub_bin: Path):
    """I1: a passphrase or credential prompt is an unbounded hang.

    `run.sh` must put git into batch mode for everything it and the skill run.
    """
    write_stub(
        stub_bin, "claude",
        'env > "$DAILY_POST_REPO/env.txt"; echo published > "$DAILY_POST_STATUS"',
    )
    run(fake_repo, stub_bin)
    env = (fake_repo / "env.txt").read_text(encoding="utf-8")
    assert "GIT_TERMINAL_PROMPT=0" in env
    assert "BatchMode=yes" in env


def test_exit_70_when_post_content_lands_on_master(fake_repo: Path, stub_bin: Path):
    """I3: the publish boundary needs a mechanical backstop.

    "No post content reaches master unreviewed" cannot rest on the model
    reproducing its instructions correctly every run. If a post file is
    committed to master during the run, that must fail loudly.
    """
    write_stub(
        stub_bin, "claude",
        'set -e\n'
        'cd "$DAILY_POST_REPO"\n'
        f'echo body > "_posts/{TODAY}-leaked.md"\n'
        'git add -A\n'
        'git commit -qm "leaked a post onto master"\n'
        'echo published > "$DAILY_POST_STATUS"',
    )
    result = run(fake_repo, stub_bin)
    assert result.returncode == 70, result.stdout + result.stderr
    output = result.stdout + result.stderr
    assert "boundary" in output.lower()
    assert "leaked" in output


def test_queue_bookkeeping_on_master_is_allowed(fake_repo: Path, stub_bin: Path):
    """The counterpart to the test above: queue state is *supposed* to land on
    master, so the boundary check must not fire on it."""
    (fake_repo / "_data").mkdir()
    write_stub(
        stub_bin, "claude",
        'set -e\n'
        'cd "$DAILY_POST_REPO"\n'
        'echo "topics: []" > _data/topic_queue.yml\n'
        'git add -A\n'
        'git commit -qm "daily-post: claim a topic"\n'
        'echo published > "$DAILY_POST_STATUS"',
    )
    result = run(fake_repo, stub_bin)
    assert result.returncode == 0, result.stdout + result.stderr


def test_old_logs_and_scratch_directories_are_rotated(fake_repo: Path, stub_bin: Path):
    """Logs and scratch dirs live under .git, so nothing else ever reaps them."""
    import os
    import time

    old_time = time.time() - 40 * 86400
    log_dir = fake_repo / ".git" / "daily-post-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stale_log = log_dir / "2000-01-01.log"
    stale_log.write_text("old", encoding="utf-8")
    os.utime(stale_log, (old_time, old_time))

    scratch = fake_repo / ".git" / "daily-post-scratch" / "2000-01-01"
    scratch.mkdir(parents=True)
    (scratch / "research.md").write_text("old", encoding="utf-8")
    os.utime(scratch, (old_time, old_time))

    run(fake_repo, stub_bin)
    assert not stale_log.exists(), "a 40-day-old log was not rotated"
    assert not scratch.exists(), "a 40-day-old scratch directory was not rotated"
    assert (log_dir / f"{TODAY}.log").is_file(), "today's log must survive rotation"


def test_exit_40_when_the_log_directory_cannot_be_created(fake_repo: Path, stub_bin: Path):
    """An unchecked `mkdir -p` means logging silently vanishes — and the log is
    the only record an unattended run leaves."""
    (fake_repo / ".git" / "daily-post-logs").mkdir(parents=True, exist_ok=True)
    # Replace the directory with a regular file so mkdir -p cannot succeed.
    import shutil

    shutil.rmtree(fake_repo / ".git" / "daily-post-logs")
    (fake_repo / ".git" / "daily-post-logs").write_text("not a directory", encoding="utf-8")
    result = run(fake_repo, stub_bin)
    assert result.returncode == 40, result.stdout + result.stderr
    assert "log" in (result.stdout + result.stderr).lower()


def test_exit_71_when_the_run_leaves_the_tree_dirty(fake_repo: Path, stub_bin: Path):
    """S5: every stopping point in the skill is supposed to end on a clean
    master. When one does not, the damage otherwise lands on TOMORROW's run as
    exit 40, a day away from the run that caused it and with a log that says
    nothing about it. Assert it here, while the explaining log is open.
    """
    write_stub(
        stub_bin, "claude",
        'set -e\n'
        'cd "$DAILY_POST_REPO"\n'
        'echo leftover > stray-uncommitted-file.txt\n'
        'echo published > "$DAILY_POST_STATUS"',
    )
    result = run(fake_repo, stub_bin)
    assert result.returncode == 71, result.stdout + result.stderr
    output = result.stdout + result.stderr
    assert "dirty tree" in output.lower()
    assert "stray-uncommitted-file.txt" in output
    # left in place on purpose, so the operator can see what happened
    assert (fake_repo / "stray-uncommitted-file.txt").exists()


def test_the_skill_does_not_inherit_the_lock_file_descriptor(fake_repo: Path, stub_bin: Path):
    """S3: fd 9 holds the flock and is inherited by children by default. An
    orphaned descendant that outlives the timeout would keep the lock held
    forever, wedging every later run at exit 31.
    """
    write_stub(
        stub_bin, "claude",
        'if [[ -e /proc/self/fd/9 ]]; then echo INHERITED > "$DAILY_POST_REPO/fd9.txt"; '
        'else echo CLOSED > "$DAILY_POST_REPO/fd9.txt"; fi\n'
        'echo published > "$DAILY_POST_STATUS"',
    )
    run(fake_repo, stub_bin)
    assert (fake_repo / "fd9.txt").read_text(encoding="utf-8").strip() == "CLOSED"


def test_the_timeout_escalates_to_sigkill(fake_repo: Path, stub_bin: Path):
    """S3: a child that traps or ignores SIGTERM must still die, or the run
    hangs on past its timeout still holding the lock."""
    text = RUN_SH.read_text(encoding="utf-8")
    assert "timeout -k 60" in text, "timeout has no kill-after; SIGTERM can be ignored"
