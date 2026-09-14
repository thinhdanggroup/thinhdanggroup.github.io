#!/usr/bin/env bash
# Run everything CI runs, locally, before the daily pipeline pushes a branch.
#
#   script/daily_post/preflight.sh          front matter + jekyll build + htmlproofer
#   script/daily_post/preflight.sh --fast   front matter only
#
# Three exit codes, because "the post is broken" and "this machine cannot check the
# post" are different situations and the pipeline acts on them differently:
#
#   0  GREEN   — every check ran and passed.
#   1  RED     — a check ran and genuinely failed (front matter, jekyll build, or
#                htmlproofer). The post is implicated. Pushing a branch CI will
#                reject only moves the failure somewhere noisier, so this is a hard
#                stop for the pipeline.
#   2  ENVIRONMENT — the checks could not be run at all: python3 missing, bundler
#                missing or not on PATH, or `bundle exec jekyll` not runnable.
#                Nothing was learned about the post, so nothing about the post may
#                be undone on the strength of this. SKILL.md Stage 5 keeps the draft
#                and the topic claim exactly as they are on a 2.
#
# The commonest cause of a 2 under cron: bundler is installed into the user gem
# directory, which an interactive shell has on PATH and cron does not. Fix with
#   export PATH="$(ruby -e 'print Gem.user_dir')/bin:$PATH"
set -uo pipefail

ENV_FAILURE=2

# Resolved with parameter expansion and shell builtins only. `$(dirname ...)` needs
# an external binary, and on a PATH thin enough to be missing bundler it can also be
# missing dirname — which used to leave REPO as "/" and made the front matter check
# fail as if the POST were broken. Resolving the root must never be able to
# masquerade as a red post.
SCRIPT_DIR="${BASH_SOURCE[0]%/*}"
[[ "$SCRIPT_DIR" == "${BASH_SOURCE[0]}" ]] && SCRIPT_DIR="."

if ! cd "$SCRIPT_DIR/../.."; then
  echo "preflight: ENVIRONMENT PROBLEM — cannot reach the repo root from" >&2
  echo "'${BASH_SOURCE[0]}'. Nothing was checked." >&2
  exit "$ENV_FAILURE"
fi
REPO="$PWD"

if [[ ! -f "$REPO/script/check_frontmatter.py" ]]; then
  echo "preflight: ENVIRONMENT PROBLEM — '$REPO' does not look like this repo" >&2
  echo "(script/check_frontmatter.py is missing). Nothing was checked." >&2
  exit "$ENV_FAILURE"
fi

FAST=0
[[ "${1:-}" == "--fast" ]] && FAST=1

if ! command -v python3 >/dev/null 2>&1; then
  echo "preflight: ENVIRONMENT PROBLEM — python3 not found on PATH, so the front" >&2
  echo "matter check could not run. This says nothing about the post." >&2
  exit "$ENV_FAILURE"
fi

echo "==> front matter contract"
if ! python3 script/check_frontmatter.py; then
  echo "preflight: RED — the front matter contract check failed. This is a problem" >&2
  echo "with the post, not with the environment." >&2
  exit 1
fi

if [[ "$FAST" -eq 1 ]]; then
  echo "==> preflight OK (fast mode: build and link checks skipped)"
  exit 0
fi

if ! command -v bundle >/dev/null 2>&1; then
  echo "preflight: ENVIRONMENT PROBLEM — bundler ('bundle') is not on PATH, so the" >&2
  echo "build and link checks could not run. This says nothing about the post." >&2
  echo "Run 'make install', and if bundler is installed but still not found, put the" >&2
  echo "user gem dir on PATH: export PATH=\"\$(ruby -e 'print Gem.user_dir')/bin:\$PATH\"" >&2
  exit "$ENV_FAILURE"
fi

if ! bundle exec jekyll --version >/dev/null 2>&1; then
  echo "preflight: ENVIRONMENT PROBLEM — 'bundle exec jekyll' is not runnable (gems" >&2
  echo "not installed for this Gemfile, or a broken bundle), so the build and link" >&2
  echo "checks could not run. This says nothing about the post. Run 'make install'." >&2
  exit "$ENV_FAILURE"
fi

echo "==> jekyll build"
if ! JEKYLL_ENV=production bundle exec jekyll build --trace; then
  echo "preflight: RED — the jekyll build failed. The environment is fine; this is a" >&2
  echo "problem with the post or the site content." >&2
  exit 1
fi

echo "==> internal links and images"
# External links are deliberately unchecked, matching .github/workflows/ci.yml:
# third-party sites rate-limit and go down, which would fail runs for unrelated reasons.
if ! bundle exec htmlproofer ./_site \
  --disable-external \
  --checks Links,Images,Scripts \
  --ignore-urls "/^#/" \
  --no-enforce-https \
  --swap-urls "^/:/"; then
  echo "preflight: RED — htmlproofer found broken internal links or images. The" >&2
  echo "environment is fine; this is a problem with the post or the site content." >&2
  exit 1
fi

echo "==> preflight OK"
