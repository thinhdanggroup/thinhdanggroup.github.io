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

**Every run must also end on a clean `master`**, checked out locally, matching
`origin/master` — exactly what `run.sh`'s own precondition (`git status --porcelain`
empty, then `git pull --ff-only origin master`) expects to find before its *next*
invocation. A run that stops on a feature branch, or with an uncommitted change sitting
in the tree, does not fail loudly today — it silently turns tomorrow's run into a hard
failure (exit 40) or bases tomorrow's post on today's abandoned branch. Every stopping
point below says explicitly how to leave the tree clean; none of that is optional.

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

If the queue is empty, discover a candidate using `references/sources.md`. Discovery
is bounded too: at most three discovered candidates total, the same cap as below — a
barren discovery pass that turns up nothing checkable still counts against that limit,
so the loop is finite either way.

Check it against the archive with `script/daily_post/dupe_check.py`:

```bash
python3 script/daily_post/dupe_check.py --title "<title>" --angle "<angle>" --json
```

Exit 1 means duplicate.

- **If the rejected candidate came from the queue** (it has a topic id), mark it
  `rejected` immediately, before moving on — via `script/daily_post/queue.py` —
  so `next_queued()` never hands the same known duplicate back on a future run:

  ```bash
  python3 -c "
  from pathlib import Path
  from script.daily_post.queue import mark
  mark(Path('_data/topic_queue.yml'), '<topic-id>', 'rejected')
  "
  ```

- **If the rejected candidate was discovered** (the queue was dry, so it has no queue
  entry), there is nothing to mark in the queue file — just try the next one.

Move to the next queue item or discover another candidate. **After three rejected
candidates in total, write `no-topic` to `$DAILY_POST_STATUS` and stop.** Before
stopping, if any `mark(..., 'rejected')` call above actually changed
`_data/topic_queue.yml`, commit and push that change **directly to `master`** — no
branch, no PR; this is queue bookkeeping, not post content — so the rejection persists
for tomorrow's run and the tree is left clean behind it:

```bash
git add _data/topic_queue.yml
git commit -m "daily-post: mark rejected topics from $(date +%F)"
git push origin master
echo no-topic > "$DAILY_POST_STATUS"
```

Skip that commit if `_data/topic_queue.yml` has no changes (every rejection this run
was a discovered candidate, never a queue entry).

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

Use a concrete scratch directory, `.git/daily-post-scratch/$(date +%F)/` — inside
`.git` so it is never tracked or committed (the same place `run.sh` already keeps its
own logs) and so it survives the branch checkout and cleanup in Stage 5:

```bash
mkdir -p ".git/daily-post-scratch/$(date +%F)"
```

Write the evidence ledger to
`.git/daily-post-scratch/$(date +%F)/research.md` — one entry per claim, each
carrying the claim, the source URL, and a verbatim supporting quote. The format is in
`references/sources.md`.

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
message**. Subagents do not inherit this session's open files, so **include these
concrete paths in each dispatch prompt** — an agent following this literally will
otherwise dispatch gates that cannot find their inputs:

- **Every gate:** the draft post path, `_posts/$(date +%F)-<slug>.md`.
- **Gate 1 (fact) and Gate 2 (duplicate):** the research ledger path,
  `.git/daily-post-scratch/$(date +%F)/research.md`.
- **Gate 2 (duplicate) only:** the `dupe_check` JSON from Stage 1, with its nearest
  matches, included inline in the dispatch prompt.

Each gate returns the JSON verdict defined in `gates.md`.

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

**If preflight is red:** fix what it reports and run it again. Never push a branch
that CI will reject. If it is still red after one fix, stop **without** ever creating
a branch — nothing has been committed yet at this point, so returning to a clean
`master` just means discarding this run's uncommitted work:

```bash
git checkout -- _data/topic_queue.yml
rm -f "_posts/$(date +%F)-<slug>.md"
rm -rf "assets/images/<slug>"
echo preflight-failed > "$DAILY_POST_STATUS"
```

This puts the claimed topic back to `queued` on disk (discarding Stage 1's `claim()`),
so a future run can retry it once the underlying preflight problem is fixed, rather
than leaving it stuck `claimed` forever with no PR to review. Any topics rejected
earlier in this same run are discarded too — an acceptable cost, since preflight
failures are environmental, not topic-specific, and a discarded rejection just costs
one retry attempt on a future run, not correctness.

**Once preflight is green**, commit and open the PR. The two outcomes below differ in
one thing — whether `mark()` runs before the commit — because the queue file must be
committed in its **final** state, not the state Stage 1 left it in:

**Gates green:** mark the topic published — via `script/daily_post/queue.py` — *before*
staging anything, then commit, push, and open the PR:

```bash
python3 -c "
from pathlib import Path
from script.daily_post.queue import mark
mark(Path('_data/topic_queue.yml'), '<topic-id>', 'published', slug='<slug>')
"
git checkout -b "daily-post/$(date +%F)-<slug>"
git add "_posts/$(date +%F)-<slug>.md" "assets/images/<slug>" _data/topic_queue.yml
git commit -m "<post title>"
git push -u origin "daily-post/$(date +%F)-<slug>"
gh pr create --title "<post title>" --body "<summary + sources used>"
```

Then return to a clean `master` and write the status — **every** terminating path
must end here, on `master`, not on the feature branch:

```bash
git checkout master
git branch -D "daily-post/$(date +%F)-<slug>" 2>/dev/null || true
echo published > "$DAILY_POST_STATUS"
```

The branch still lives on `origin` for the open PR; deleting only the local copy is
what keeps `run.sh`'s own `daily-post/<date>-*` idempotency check meaningful for a
genuine second run.

**Gates still blocked after two revision rounds:** the topic must stay `claimed` —
that is already its status from Stage 1's `claim()`, so do **not** call `mark()`
again here. Commit exactly what is already on disk, in the same order (nothing writes
to the queue file between the claim and this commit):

```bash
git checkout -b "daily-post/$(date +%F)-<slug>"
git add "_posts/$(date +%F)-<slug>.md" "assets/images/<slug>" _data/topic_queue.yml
git commit -m "<post title> [needs work]"
git push -u origin "daily-post/$(date +%F)-<slug>"
gh pr create --draft --title "<post title> [needs work]" \
  --body "<every gate's full verdict>"
gh pr edit --add-label needs-work
```

Then return to a clean `master` and write the status, exactly as on the green path:

```bash
git checkout master
git branch -D "daily-post/$(date +%F)-<slug>" 2>/dev/null || true
echo blocked > "$DAILY_POST_STATUS"
```

Leave the topic `claimed` in that case — it is neither published nor rejected, and the
operator decides which it becomes by reading the draft PR.

## Failure handling

Any unrecoverable error: write the closest matching token to `$DAILY_POST_STATUS`,
explain what happened in the transcript, and stop. Never leave the status file empty —
`run.sh` reports that as exit 50, which is indistinguishable from a crash.

Before stopping on any error, return the tree to a clean `master` the same way as the
paths above: if `_data/topic_queue.yml` was legitimately updated this run (a
`rejected` mark), commit and push that directly to `master`; otherwise discard
whatever this run touched (`git checkout -- _data/topic_queue.yml`, remove any
untracked draft or banner files, delete any local feature branch this run created).
Never leave `master` dirty or checked out on a feature branch — that silently breaks
tomorrow's run instead of failing loudly today.
