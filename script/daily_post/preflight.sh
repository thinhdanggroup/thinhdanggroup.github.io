#!/usr/bin/env bash
# Run everything CI runs, locally, before the daily pipeline pushes a branch.
#
#   script/daily_post/preflight.sh          front matter + jekyll build + htmlproofer
#   script/daily_post/preflight.sh --fast   front matter only
#
# Exits 0 when green, 1 when red. A red preflight is a hard stop for the pipeline:
# pushing a branch that CI will reject just moves the failure somewhere noisier.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO"

FAST=0
[[ "${1:-}" == "--fast" ]] && FAST=1

echo "==> front matter contract"
python3 script/check_frontmatter.py

if [[ "$FAST" -eq 1 ]]; then
  echo "==> preflight OK (fast mode: build and link checks skipped)"
  exit 0
fi

if ! command -v bundle >/dev/null 2>&1; then
  echo "preflight: bundler not found; run 'make install' first" >&2
  exit 1
fi

echo "==> jekyll build"
JEKYLL_ENV=production bundle exec jekyll build --trace

echo "==> internal links and images"
# External links are deliberately unchecked, matching .github/workflows/ci.yml:
# third-party sites rate-limit and go down, which would fail runs for unrelated reasons.
bundle exec htmlproofer ./_site \
  --disable-external \
  --checks Links,Images,Scripts \
  --ignore-urls "/^#/" \
  --no-enforce-https \
  --swap-urls "^/:/"

echo "==> preflight OK"
