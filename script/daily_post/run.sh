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
#       locally or on origin, or another run currently holds the lock)
#   40  precondition failed (git/claude/gh/python3/flock missing, not a git
#       repository, gh unauthenticated, dirty tree, stale master, ruamel.yaml
#       missing, lock file could not be opened/locked for a reason other than
#       another run holding it)
#   50  pipeline failure (preflight red, or the skill reported nothing)
#
# Environment:
#   DAILY_POST_REPO       repo path (default: two levels up from this script)
#   DAILY_POST_SKIP_PULL  set to 1 to skip the git pull (tests, offline runs)
set -uo pipefail

REPO="${DAILY_POST_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$REPO" || { echo "run.sh: cannot cd to $REPO" >&2; exit 40; }

TODAY="$(date +%F)"
LOG_DIR="$REPO/.git/daily-post-logs"
LOG="$LOG_DIR/$TODAY.log"
mkdir -p "$LOG_DIR"

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

# --- concurrency guard --------------------------------------------------
# An overlapping cron fire, or a manual run on top of a scheduled one, must not
# run two pipelines against the same working directory at once. Take an
# exclusive, non-blocking lock; if another run already holds it, this is the
# same operator-facing outcome as "already ran today": nothing to do.
LOCK="$REPO/.git/daily-post.lock"
if ! exec 9>"$LOCK"; then
  die "cannot open lock file $LOCK"
fi
flock -n 9
FLOCK_RC=$?
case "$FLOCK_RC" in
  0) ;; # acquired, carry on
  1) log "another daily-post run is already in progress; nothing to do"
     exit 30 ;;
  *) die "flock failed (rc=$FLOCK_RC)" ;;
esac

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

log "invoking the daily-post skill"
claude -p "/daily-post" >>"$LOG" 2>&1
CLAUDE_RC=$?
log "claude exited $CLAUDE_RC"

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
