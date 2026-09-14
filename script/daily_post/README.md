# Daily post pipeline scripts

Supporting scripts for the `daily-post` skill in `.claude/skills/daily-post/`.
Run them from the repo root so the `script.daily_post` import path resolves.

## Install

```bash
pip install -r script/daily_post/requirements.txt
```

`run.sh` checks for `ruamel.yaml` (one of this file's pinned dependencies) as a
precondition and fails fast with exit `40` if it is missing.

| File | Responsibility |
| --- | --- |
| `run.sh` | Daily entry point: preconditions, idempotency, exit codes, logging |
| `preflight.sh` | Front matter + jekyll build + htmlproofer, exactly as CI runs them. `0` green, `1` a check failed, `2` the environment cannot run the checks |
| `similarity.py` | TF-IDF and cosine, standard library only |
| `corpus.py` | Reads `_posts/*.md` into comparable records |
| `dupe_check.py` | CLI: is this topic a duplicate? Exit 1 means yes |
| `queue.py` | Read and update `_data/topic_queue.yml` |
| `make_banner.py` | SVG-authored `banner.webp`, `teaser.webp` and the `banner.svg` source; falls back to Pillow without `cairosvg` |

`make daily-post-dupe TITLE="..."` exits `1` when the title IS a duplicate — that is
the answer, not a failure — so `make` prints `Error 1` underneath the
`DUPLICATE top score ...` line; read the score line, not the `Error 1`.

## Exit codes

`run.sh`'s header carries the authoritative list; this is the same table the root
`README.md` shows operators.

| Code | Meaning |
| --- | --- |
| `0` | Gates green, PR open |
| `10` | Blocked after two revisions; draft PR open |
| `20` | No viable topic after three attempts |
| `30` | Already ran today — a post or branch for today already exists |
| `31` | Another run currently holds the lock. Separate from `30` on purpose: `30` is benign, but a `31` that repeats means a previous run hung and is still holding the lock, which silently stops the pipeline |
| `40` | Precondition failed (missing tool, not a git repo, `gh` unauthenticated, **`master` not checked out**, dirty tree, stale `master`, log dir not creatable, lock unopenable) |
| `50` | Preflight red (`preflight.sh` exit `1` or `2`), or the skill reported no status. On a `2` the environment is broken, not the post: the draft and the topic's `claimed` state are deliberately preserved — fix the machine and re-run |
| `60` | The skill exceeded `DAILY_POST_TIMEOUT` (default 3600s) and was killed. Deliberately not `30` — a hung run must never report "nothing to do" |
| `70` | Publish-boundary violation: files other than `_data/topic_queue.yml` landed on local `master`. `run.sh` pushes nothing itself, but the skill pushes queue state during Stages 1 and 5 — inspect `origin/master` as well as local `master` |
| `71` | The run finished with an unclean working tree. Left in place for inspection; otherwise it surfaces as tomorrow's exit `40`, a day away from the run that caused it. A `preflight.sh` exit `2` reaches the operator this way rather than as `50`: the draft is deliberately kept in the tree, so the tree is deliberately dirty |

`run.sh` exports `GIT_TERMINAL_PROMPT=0` and a `BatchMode=yes` `GIT_SSH_COMMAND` so no
git operation can block on a passphrase or credential prompt, and it reaps
`.git/daily-post-logs/` and `.git/daily-post-scratch/` entries older than 30 days.

## preflight.sh exit codes

`preflight.sh` distinguishes a broken post from a broken machine, because the skill
acts on them differently:

| Code | Meaning | What Stage 5 does |
| --- | --- | --- |
| `0` | Green — every check ran and passed | Branch, PR, publish |
| `1` | Red — a check ran and failed (front matter, jekyll build, htmlproofer) | The post is implicated: a queue-sourced topic goes back to `queued` and the draft is moved aside to `.git/daily-post-scratch/` |
| `2` | Environment — the checks could not run at all (python3 or bundler missing/not on `PATH`, `bundle exec jekyll` not runnable) | **Nothing is undone.** The post was never checked, so the draft and the topic's `claimed` state are both left exactly as they are; the run still writes `preflight-failed` so the operator investigates |

The `2` path exists because the commonest environment failure is invisible: bundler
installed into the user gem directory, which an interactive shell has on `PATH` and
cron does not. Without a distinct code, that shows up as an ordinary red preflight —
and a good, finished post gets silently discarded. Put the gem dir on `PATH` before
running under a scheduler:

```bash
export PATH="$(ruby -e 'print Gem.user_dir')/bin:$PATH"
```

## Permissions

`.claude/settings.json` (repo root) is the allowlist the headless `claude -p` run
executes under. Read it before the first run. It is scoped to the commands the five
stages actually issue.

It is a guard against **accidents**, and the reason nobody has to reach for a blanket
bypass. It is **not** a security boundary against a compromised or prompt-injected
agent: `Bash(python3 -c:*)` is arbitrary Python no deny rule inspects, `cat`/`grep`
read anything the user can read (`Read()` deny rules govern the `Read` tool, not shell
commands), and `echo` with a redirection writes outside the `Write(_posts/**)`
confinement. Size the trust accordingly — and do not reach for
`--dangerously-skip-permissions`: a blanket bypass on an unattended run with push
rights is the configuration this design was built to avoid. See the root `README.md`
for what it grants and denies.

## Why standard library only (text)

`scikit-learn` and `numpy` are installed on the target machine but broken
(`ImportError: numpy.core.multiarray failed to import`). The corpus is ~150 short
documents, far too small for those dependencies to earn their place, so the TF-IDF
implementation is hand-rolled in `similarity.py`.

## Banner rendering

`make_banner.py` has two renderers and picks the first that works:

| Renderer | When | Output |
| --- | --- | --- |
| **SVG + `cairosvg`** (preferred) | `import cairosvg` succeeds | `banner.webp`, `teaser.webp`, **and `banner.svg`** — the vector source the rasters were rendered from, shipped next to them in `assets/images/<slug>/` so the art stays editable |
| **Pillow** (fallback) | `cairosvg` cannot be imported | `banner.webp` and `teaser.webp` only. A note goes to **stderr**, the run continues at exit `0`, and any stale `banner.svg` from an earlier run is removed so the directory never advertises a source that does not match its rasters |

`cairosvg` is listed in `requirements.txt` but is deliberately **optional**: it needs
`libcairo` at runtime, and a scheduler box may not have it. Losing the nicer artwork
for a day is a small cost; failing a whole pipeline run over a decorative image is
not. This is the same class of failure the bundler/`PATH` problem caused, so it is
handled the same way — degrade and say so, never crash.

SVG is the authoring format because it is far more expressive than Pillow's
primitives: real radial gradients, multi-stop ramps, per-element opacity, clip paths
and bezier strokes of varying width. What `cairosvg` 2.9.1 does **not** support, all
of which fail silently rather than erroring — verified by probe, do not reach for
them: `feGaussianBlur` (renders unblurred), `feTurbulence` (renders black), `<mask>`
(ignored), and a gradient paint on a `stroke` (renders nothing).

Both renderers are bound by the same tested contract: no text in the image (the
theme paints the post's own `h1` on top), byte-identical output for the same
title/category/slug across processes and `PYTHONHASHSEED` values, visible variation
between slugs, and WCAG AA (≥ 4.5:1) for white title text under the theme's 50%
black overlay, for every one of the seven categories.

The remaining tools are still absent: no `rsvg-convert`, no ImageMagick, no `cwebp`.
Pillow writes WebP natively.

## Known limitation: duplicate recall

The 0.55 TF-IDF gate (`dupe_check.py`, `make daily-post-dupe`) is a cheap mechanical
pre-filter, not a guarantee. Measured against the live archive, it catches
near-identical titles but misses paraphrases of the same underlying topic:

```
"Migrating from Kafka to NATS"                  0.599  flagged
"Kafka to NATS migration guide"                 0.564  flagged
"Moving off Kafka onto NATS"                    0.489  MISSED
"Replacing our message broker: Kafka to NATS"   0.377  MISSED
"Why we switched messaging systems from Kafka"  0.328  MISSED
```

All five sentences describe the same post. Only the two that share most of the same
words score above threshold. Gate 2 (the semantic duplicate gate in the skill, run
during Stage 4 review) is what actually catches the other three — it reads the
candidate and the nearest matches for meaning, not just token overlap. Do not trust
`make daily-post-dupe` output alone to mean a topic is fresh.

## Editing the queue by hand

The queue round-trips through `ruamel.yaml` so your comments survive a `claim()`, but
an inline (end-of-line) comment on a topic's **last field** gets reattached to the
`claimed_on:` field the pipeline adds, e.g.:

```yaml
status: queued  # waiting on the 0.19 release   <-- avoid this
```

becomes, after a run:

```yaml
status: claimed
claimed_on: '2026-09-14' # waiting on the 0.19 release
```

Nothing is lost and nothing breaks, but the note now reads as if it annotates the
claim date. Put per-topic notes on their own line above the entry, or in the file's
header block, rather than inline on the last field.

## Tests

```bash
make daily-post-test                                  # everything
python3 -m pytest script/daily_post/tests -m "not slow"  # skip the full site build
```

The `slow` marker covers the full Jekyll build; the `calibration` marker covers the
duplicate threshold pinned against the live archive. If the calibration test fails
after the archive grows, re-tune `DEFAULT_THRESHOLD` — do not weaken the assertion.
