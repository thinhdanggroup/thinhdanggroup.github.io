#!/usr/bin/env bash
# Daily entry point for the blog post pipeline. Point your scheduler at this.
#
#   script/daily_post/run.sh
#
# Exit codes:
#   0   post written, gates green, PR open
#   10  gates still blocked after two revisions; draft PR open
#   20  no viable topic after three attempts
#   30  already ran today; nothing done (post/branch for today already exists,
#       locally or on origin)
#   31  another run currently holds the lock. Distinct from 30 on purpose: 30 is
#       benign and the operator is told to ignore it, but a lock held run after
#       run means a previous run hung and is still holding it, which silently
#       stops the pipeline. Investigate a 31 that repeats.
#   40  precondition failed (git/claude/gh/python3/flock/timeout missing, not a
#       git repository, gh unauthenticated, not on master, dirty tree, stale
#       master, ruamel.yaml missing, log directory not creatable, lock file
#       could not be opened/locked for a reason other than another run holding it)
#   50  pipeline failure (preflight red, or the skill reported nothing)
#   60  the skill exceeded DAILY_POST_TIMEOUT and was killed. Never reported as
#       30: a hung run that reports "nothing to do" is the pipeline quietly
#       dying while claiming to be healthy.
#   70  publish-boundary violation: the run put something other than
#       _data/topic_queue.yml onto local master. Post content must reach master
#       only through a reviewed PR. run.sh pushes nothing itself, but the skill
#       pushes on its own during Stages 1 and 5 — check origin/master too.
#   71  the run finished with an unclean working tree. Left in place for
#       inspection; tomorrow's run would otherwise fail its precondition (40)
#       a day away from the run that caused it.
#
# Environment:
#   DAILY_POST_REPO       repo path (default: two levels up from this script)
#   DAILY_POST_SKIP_PULL  set to 1 to skip the git pull (tests, offline runs)
#   DAILY_POST_TIMEOUT    seconds before the skill is killed (default: 3600)
set -uo pipefail

# The pipeline is unattended: nothing may ever block on an interactive prompt.
# git over SSH will happily sit forever on a key passphrase or a host-key
# confirmation, and git over HTTPS on a credential prompt — each one a hang that
# holds the lock and stops every later run.
export GIT_TERMINAL_PROMPT=0
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new}"

REPO="${DAILY_POST_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$REPO" || { echo "run.sh: cannot cd to $REPO" >&2; exit 40; }

TODAY="$(date +%F)"
LOG_DIR="$REPO/.git/daily-post-logs"
SCRATCH_DIR="$REPO/.git/daily-post-scratch"
LOG="$LOG_DIR/$TODAY.log"
# Unchecked, a failure here loses every log line the run would have written —
# the pipeline then fails silently and invisibly. `log` is not usable yet.
mkdir -p "$LOG_DIR" || {
  echo "run.sh: cannot create log directory $LOG_DIR" >&2
  exit 40
}

log() { echo "[$(date +%T)] $*" | tee -a "$LOG"; }
die() { log "PRECONDITION FAILED: $*"; exit 40; }

# --- preconditions, checked before any expensive work -----------------------
command -v git >/dev/null 2>&1 || die "git is not installed"
git rev-parse --git-dir >/dev/null 2>&1 || die "not a git repository: $REPO"
command -v claude >/dev/null 2>&1 || die "claude is not installed"
command -v gh >/dev/null 2>&1 || die "gh is not installed; the PR step needs it"
gh auth status >/dev/null 2>&1 || die "gh cannot authenticate; run 'gh auth login'"
command -v python3 >/dev/null 2>&1 || die "python3 is not installed"
python3 -c "import ruamel.yaml" >/dev/null 2>&1 \
  || die "ruamel.yaml is not installed; pip install -r script/daily_post/requirements.txt"
command -v flock >/dev/null 2>&1 || die "flock is not installed; required for the concurrency guard"
command -v timeout >/dev/null 2>&1 || die "timeout is not installed; required to bound the skill invocation"

# The whole pipeline assumes master: it pulls master, pushes queue state to
# master, and branches off master. On any other branch `git pull --ff-only
# origin master` fast-forwards whatever is checked out, and every later
# `git push origin master` pushes that ref instead — silently orphaning the
# queue commits this run depends on.
if ! CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>&1)"; then
  die "cannot determine the current branch: $CURRENT_BRANCH"
fi
[[ "$CURRENT_BRANCH" == "master" ]] \
  || die "master is not checked out (HEAD is on '$CURRENT_BRANCH'); run 'git checkout master' first"

# --- concurrency guard --------------------------------------------------
# An overlapping cron fire, or a manual run on top of a scheduled one, must not
# run two pipelines against the same working directory at once. Take an
# exclusive, non-blocking lock. A held lock exits 31, NOT 30: "already ran
# today" (30) is benign and operators are told to ignore it, but a lock that
# stays held is how a hung run stops the pipeline while every later invocation
# reports nothing-to-do. The two must be distinguishable from the exit code
# alone, or a stuck pipeline looks exactly like a healthy idle one.
LOCK="$REPO/.git/daily-post.lock"
if ! exec 9>"$LOCK"; then
  die "cannot open lock file $LOCK"
fi
flock -n 9
FLOCK_RC=$?
case "$FLOCK_RC" in
  0) ;; # acquired, carry on
  1) log "LOCK HELD: another daily-post run still holds $LOCK; nothing done. If this repeats, a previous run is hung — check $LOG_DIR and kill it."
     exit 31 ;;
  *) die "flock failed (rc=$FLOCK_RC)" ;;
esac

# --- rotation ---------------------------------------------------------------
# Logs and scratch dirs live under .git and are never committed, so nothing
# reaps them. Both paths are fixed literals under a verified git repo — not
# built from any substituted value.
find "$LOG_DIR" -maxdepth 1 -type f -mtime +30 -delete 2>/dev/null || true
if [[ -d "$SCRATCH_DIR" ]]; then
  find "$SCRATCH_DIR" -mindepth 1 -maxdepth 1 -mtime +30 -exec rm -rf -- {} + 2>/dev/null || true
fi

# --- working tree / remote state --------------------------------------------
# Distinguish "git command failed" from "git succeeded and reports clean" —
# under `set -uo pipefail` (no `-e`) a failed git command with empty stdout
# reads identically to a clean, negative result unless checked explicitly.
if ! STATUS_OUT="$(git status --porcelain 2>&1)"; then
  die "git status failed: $STATUS_OUT"
fi
[[ -z "$STATUS_OUT" ]] || die "working tree is not clean"

if [[ "${DAILY_POST_SKIP_PULL:-0}" != "1" ]]; then
  log "pulling master"
  git pull --ff-only --quiet origin master >>"$LOG" 2>&1 \
    || die "could not fast-forward master"
fi

# --- idempotency ------------------------------------------------------------
# A double-fire, or a manual run on top of a scheduled one, must not write a
# second post for the same day.
if compgen -G "_posts/$TODAY-*.md" >/dev/null; then
  log "a post for $TODAY already exists; nothing to do"
  exit 30
fi

if ! BRANCH_OUT="$(git branch --list "daily-post/$TODAY-*" 2>&1)"; then
  die "git branch --list failed: $BRANCH_OUT"
fi
if [[ -n "$BRANCH_OUT" ]]; then
  log "a daily-post branch for $TODAY already exists locally; nothing to do"
  exit 30
fi

# A branch may have been pushed and then deleted locally (or created by a run
# on another machine); check origin too. A network hiccup here must not kill
# an otherwise-healthy run — log a warning and fall back to the local checks.
if REMOTE_BRANCH_OUT="$(git ls-remote --heads origin "daily-post/$TODAY-*" 2>&1)"; then
  if [[ -n "$REMOTE_BRANCH_OUT" ]]; then
    log "a daily-post branch for $TODAY already exists on origin; nothing to do"
    exit 30
  fi
else
  log "WARNING: could not check origin for existing daily-post branches (continuing): $REMOTE_BRANCH_OUT"
fi

# --- run the pipeline -------------------------------------------------------
STATUS_FILE="$(mktemp)"
trap 'rm -f "$STATUS_FILE"' EXIT
export DAILY_POST_STATUS="$STATUS_FILE"

# What master points at before the skill runs. Everything the skill adds to
# local master during the run is the difference between this and master
# afterwards — that difference is the publish boundary, asserted below.
if ! MASTER_BEFORE="$(git rev-parse master 2>&1)"; then
  die "cannot resolve master: $MASTER_BEFORE"
fi

TIMEOUT_SECS="${DAILY_POST_TIMEOUT:-3600}"

# `-k 60`: SIGTERM, then SIGKILL 60s later, so a child that ignores or traps
# SIGTERM still dies. `9>&-` closes the lock fd for the child: fd 9 is inherited
# by default, so an orphaned descendant that outlives the timeout would keep the
# flock held forever and wedge every later run at exit 31.
log "invoking the daily-post skill (timeout ${TIMEOUT_SECS}s, SIGKILL 60s after)"
timeout -k 60 "$TIMEOUT_SECS" claude -p "/daily-post" >>"$LOG" 2>&1 9>&-
CLAUDE_RC=$?
log "claude exited $CLAUDE_RC"

if [[ "$CLAUDE_RC" -eq 124 ]]; then
  log "TIMED OUT: the skill exceeded ${TIMEOUT_SECS}s and was killed. A run that hangs holds the lock, so every later run would exit 31 until this is cleared; see $LOG."
fi

# --- publish boundary -------------------------------------------------------
# No post content reaches master except through a reviewed PR. The skill is
# told that, but "the model reproduced the instructions correctly" is not a
# control. This is the mechanical backstop: the only path allowed to change on
# local master during a run is the queue bookkeeping file.
if ! LANDED="$(git diff --name-only "$MASTER_BEFORE" master 2>&1)"; then
  log "WARNING: could not check the publish boundary (git diff failed): $LANDED"
else
  UNEXPECTED="$(printf '%s\n' "$LANDED" | grep -v '^_data/topic_queue\.yml$' | grep -v '^$')"
  if [[ -n "$UNEXPECTED" ]]; then
    log "PUBLISH BOUNDARY VIOLATED: this run put files other than _data/topic_queue.yml onto local master:"
    log "$UNEXPECTED"
    log "Post content must reach master only through a reviewed PR. run.sh itself pushes nothing, but the skill pushes queue state during Stages 1 and 5 — check origin/master as well as local master (git log $MASTER_BEFORE..master), then reset or push deliberately by hand."
    exit 70
  fi
fi

# --- working tree, after the run --------------------------------------------
# Every stopping point in the skill is supposed to end on a clean master. When
# one does not, the damage lands on TOMORROW's run as exit 40 ("working tree is
# not clean") — a failure with no connection to the run that caused it, a day
# later. Assert it here instead, while the log that explains it is the one
# being written.
if ! POST_STATUS_OUT="$(git status --porcelain 2>&1)"; then
  log "WARNING: could not check the working tree after the run: $POST_STATUS_OUT"
elif [[ -n "$POST_STATUS_OUT" ]]; then
  log "DIRTY TREE AFTER RUN: the skill left uncommitted changes behind:"
  log "$POST_STATUS_OUT"
  log "Left in place for inspection. Tomorrow's run will fail its precondition (exit 40) until this is resolved; see $LOG."
  exit 71
fi

if [[ "$CLAUDE_RC" -eq 124 ]]; then
  exit 60
fi

STATUS="$(tr -d '[:space:]' <"$STATUS_FILE" 2>/dev/null)"
log "pipeline status: ${STATUS:-<none>}"

case "$STATUS" in
  published) log "PR opened; review and merge"; exit 0 ;;
  blocked)   log "gates blocked; draft PR opened with the gate report"; exit 10 ;;
  no-topic)  log "no viable topic; stock _data/topic_queue.yml"; exit 20 ;;
  preflight-failed)
             log "preflight was red; see $LOG"; exit 50 ;;
  *)         log "pipeline reported no status (claude rc=$CLAUDE_RC); see $LOG"; exit 50 ;;
esac
