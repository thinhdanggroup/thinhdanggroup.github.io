---
name: daily-post
description: Research, write, review and open a PR for one blog post. Use when running the daily post pipeline, when asked to write today's post, or when invoked as /daily-post by script/daily_post/run.sh.
---

# Daily Post

Produce one researched, reviewed blog post and open a pull request for it.

**This runs unattended. Never ask the operator a question** — every decision resolves
from `_data/topic_queue.yml` or from the gate rules. There are no questions asked
during a run: a question is a hang, not a pause.

Write the run's outcome to the file named by `$DAILY_POST_STATUS` as a single token:
`published`, `blocked`, `no-topic`, or `preflight-failed`. `run.sh` maps that token to
its exit code, so a run that writes nothing is reported as a pipeline failure.

Read these before starting:

- `references/frontmatter.md` — the contract CI enforces
- `references/voice.md` — what the blog sounds like
- `references/sources.md` — where to research, and the evidence ledger format
- `references/gates.md` — the four gates and their verdict schema

---

## Stage 1 — Select a topic

Read the queue via `script/daily_post/queue.py`:

```bash
python3 -c "
from pathlib import Path
from script.daily_post.queue import load_topics, next_queued
t = next_queued(load_topics(Path('_data/topic_queue.yml')))
print(t.id, '|', t.title, '|', t.angle, '|', t.category) if t else print('EMPTY')
"
```

If the queue is empty, discover a candidate using `references/sources.md`.

Check it against the archive with `script/daily_post/dupe_check.py`:

```bash
python3 script/daily_post/dupe_check.py --title "<title>" --angle "<angle>" --json
```

Exit 1 means duplicate. On a duplicate, move to the next queue item or discover
another candidate. **After three rejected candidates, write `no-topic` to
`$DAILY_POST_STATUS` and stop.**

Once a candidate passes, claim it immediately — before any research — so a second run
today cannot pick the same topic, again via `script/daily_post/queue.py`:

```bash
python3 -c "
from pathlib import Path
from script.daily_post.queue import claim
claim(Path('_data/topic_queue.yml'), '<topic-id>', on='$(date +%F)')
"
```

Keep the `dupe_check` JSON and carry its nearest matches forward to Gate 2 **even when
every one of their scores is low** — a passing mechanical score is not evidence the
topic is fresh, only a cheap pre-filter that Gate 2's semantic reading must still run
against.

## Stage 2 — Research

Gather primary sources with WebSearch and WebFetch, following `references/sources.md`.

Write the evidence ledger to `research.md` in the scratch directory — one entry per
claim, each carrying the claim, the source URL, and a verbatim supporting quote. The
format is in `references/sources.md`.

**No claim may appear in the post unless it appears in the ledger.** Write from the
ledger, not from recall. This is what makes Gate 1 possible.

## Stage 3 — Write

Write `_posts/$(date +%F)-<slug>.md`.

- 1,000–1,500 words, following `references/voice.md`
- Front matter per `references/frontmatter.md`, with `header.overlay_image` and
  `header.teaser` pointing at `/assets/images/<slug>/banner.webp` and `teaser.webp`
- One idea, one worked example, one takeaway
- Wrap any code fence containing `{{` or `{%` in `{% raw %}` … `{% endraw %}`

## Stage 4 — Review

Dispatch all four gates from `references/gates.md` as **parallel subagents in a single
message**. Each returns the JSON verdict defined there.

If every gate passes, go to Stage 5.

If any gate blocks, hand the findings to the writer and revise. **At most two revision
rounds.** After a second failed round, skip to Stage 5 in blocked mode.

## Stage 5 — Publish

Generate the banner with `script/daily_post/make_banner.py`. The banner is pure
abstract, category-tinted artwork with no title text baked in — the theme paints the
post's own `<h1>`, description and meta on top of `overlay_image` under 50%
darkening, so a title inside the image would render twice:

```bash
python3 script/daily_post/make_banner.py \
  --title "<title>" --category <category> --slug <slug>
```

Run preflight — exactly what CI runs — via `script/daily_post/preflight.sh`:

```bash
script/daily_post/preflight.sh
```

**If preflight is red:** fix what it reports and run it again. If it is still red after
one fix, write `preflight-failed` to `$DAILY_POST_STATUS` and stop. Never push a branch
that CI will reject.

Commit and open the PR:

```bash
git checkout -b "daily-post/$(date +%F)-<slug>"
git add "_posts/$(date +%F)-<slug>.md" "assets/images/<slug>" _data/topic_queue.yml
git commit -m "<post title>"
git push -u origin "daily-post/$(date +%F)-<slug>"
```

**Gates green:**

```bash
gh pr create --title "<post title>" --body "<summary + sources used>"
```

Then mark the topic published via `script/daily_post/queue.py` and write the status:

```bash
python3 -c "
from pathlib import Path
from script.daily_post.queue import mark
mark(Path('_data/topic_queue.yml'), '<topic-id>', 'published', slug='<slug>')
"
echo published > "$DAILY_POST_STATUS"
```

**Gates still blocked after two revision rounds:**

```bash
gh pr create --draft --title "<post title> [needs work]" \
  --body "<every gate's full verdict>"
gh pr edit --add-label needs-work
echo blocked > "$DAILY_POST_STATUS"
```

Leave the topic `claimed` in that case — it is neither published nor rejected, and the
operator decides which it becomes.

## Failure handling

Any unrecoverable error: write the closest matching token to `$DAILY_POST_STATUS`,
explain what happened in the transcript, and stop. Never leave the status file empty —
`run.sh` reports that as exit 50, which is indistinguishable from a crash.
