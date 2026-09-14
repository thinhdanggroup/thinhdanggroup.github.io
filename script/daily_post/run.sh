#!/usr/bin/env bash
# Daily entry point for the blog post pipeline. Point your scheduler at this.
#
#   script/daily_post/run.sh
#
# Exit codes:
#   0   post written, gates green, PR open
#   10  gates still blocked after two revisions; draft PR open
#   20  no viable topic after three attempts
#   30  already ran today; nothing done
#   40  precondition failed (gh missing or unauthenticated, dirty tree, stale master,
#       ruamel.yaml missing)
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
command -v claude >/dev/null 2>&1 || die "claude is not installed"
command -v gh >/dev/null 2>&1 || die "gh is not installed; the PR step needs it"
gh auth status >/dev/null 2>&1 || die "gh cannot authenticate; run 'gh auth login'"
python3 -c "import ruamel.yaml" >/dev/null 2>&1 \
  || die "ruamel.yaml is not installed; pip install -r script/daily_post/requirements.txt"

[[ -z "$(git status --porcelain)" ]] || die "working tree is not clean"

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

if git branch --list "daily-post/$TODAY-*" | grep -q .; then
  log "a daily-post branch for $TODAY already exists; nothing to do"
  exit 30
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
