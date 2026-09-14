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
| `preflight.sh` | Front matter + jekyll build + htmlproofer, exactly as CI runs them |
| `similarity.py` | TF-IDF and cosine, standard library only |
| `corpus.py` | Reads `_posts/*.md` into comparable records |
| `dupe_check.py` | CLI: is this topic a duplicate? Exit 1 means yes |
| `queue.py` | Read and update `_data/topic_queue.yml` |
| `make_banner.py` | Pillow-rendered `banner.webp` and `teaser.webp` |

`make daily-post-dupe TITLE="..."` exits `1` when the title IS a duplicate — that is
the answer, not a failure — so `make` prints `Error 1` underneath the
`DUPLICATE top score ...` line; read the score line, not the `Error 1`.

## Why standard library only

`scikit-learn` and `numpy` are installed on the target machine but broken
(`ImportError: numpy.core.multiarray failed to import`). The corpus is ~150 short
documents, far too small for those dependencies to earn their place, so the TF-IDF
implementation is hand-rolled in `similarity.py`.

Likewise for images: no `cairosvg`, `rsvg-convert`, ImageMagick, or `cwebp` is present.
Pillow writes WebP natively and is the only image dependency.

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
