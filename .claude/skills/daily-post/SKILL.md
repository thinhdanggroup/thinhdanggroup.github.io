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

### Queue bookkeeping and master

**Queue state is pipeline bookkeeping and lives on `master`. Post content lives in the
PR.** Every transition `queue.py` writes to `_data/topic_queue.yml` — a claim, a
rejection, a publish, a revert back to `queued` — is committed and pushed straight to
`master` at the point it happens, never bundled into a feature branch. A feature branch
carries the post and its images and nothing else.

This is what makes Stage 1's claim actually stop a second run from picking the same
topic: if the claim only ever lived on a feature branch, `master` would still read
`queued` until a human merges that branch's PR, and tomorrow's run — which starts from
`master`, not from any open PR — would pick the very same topic again, research and
write it a second time, and open a second PR for it. That repeats every day the first
PR stays open. Pushing the claim to `master` immediately is what closes that gap.

Every one of these pushes uses the same non-fatal pattern — a failed push here is
bookkeeping trouble, not a reason to fail a run that did its real work:

```bash
git add _data/topic_queue.yml
git commit -m "<what changed, e.g. 'daily-post: claim <topic-id>'>"
if ! git push origin master; then
  echo "WARNING: push to master failed (network or branch protection); the commit
  stands locally and a future successful run will push it. Until it does, this
  claim/rejection/publish mark is not durable and the topic could be picked again
  by another run." >&2
fi
```

A failed push there is never a reason to abort the run or change the status token:
finish the stage you were in and write the token the run actually earned. The
warning above is what tells the operator, from the log, why a topic might get
attempted twice while that push keeps failing.

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
  `rejected` immediately, before moving on — via `script/daily_post/queue.py` — then
  commit and push that to `master` right away, using the non-fatal pattern above, so
  `next_queued()` never hands the same known duplicate back on a future run:

  ```bash
  python3 -c "
  from pathlib import Path
  from script.daily_post.queue import mark
  mark(Path('_data/topic_queue.yml'), '<topic-id>', 'rejected')
  "
  git add _data/topic_queue.yml
  git commit -m "daily-post: mark <topic-id> rejected"
  git push origin master || echo "WARNING: push to master failed; see above." >&2
  ```

- **If the rejected candidate was discovered** (the queue was dry, so it has no queue
  entry), there is nothing to mark or commit — just try the next one.

Move to the next queue item or discover another candidate. **After three rejected
candidates in total, write `no-topic` to `$DAILY_POST_STATUS` and stop.** Nothing
further needs committing here — every rejection that touched the queue file was
already pushed to `master` as it happened.

If `dupe_check` did not reject the candidate, check it against work already in
flight before claiming anything. An open PR is work already done and awaiting
review — writing the same topic again produces two PRs competing for the same slot:

```bash
gh pr list --state open --search "daily-post" --json title,headRefName
```

If this call fails (a transient GitHub API or network problem), log it and continue
— a missing guard is not a reason to abort the run; treat the candidate as if no open
PR matched it, the same way `run.sh` itself logs a warning and falls back to its
local checks when `git ls-remote` fails.

Compare the candidate's title and angle against the open PRs' titles by judgement,
not a literal string match — a differently-worded PR covering the same underlying
argument still counts as a match. If one matches, treat the candidate exactly as a
`dupe_check` rejection above: mark it `rejected` if it came from the queue (and
commit/push that the same way), or just move on if it was discovered. Either way it
counts toward the three-candidate limit.

Once a candidate passes both checks:

- **If it came from the queue** (it has a topic id), claim it immediately — before
  any research — via `script/daily_post/queue.py`, then commit and push that to
  `master` right away, the same way, so a second run today (or tomorrow, while this
  run's eventual PR is still open) cannot pick the same topic:

  ```bash
  python3 -c "
  from pathlib import Path
  from script.daily_post.queue import claim
  claim(Path('_data/topic_queue.yml'), '<topic-id>', on='$(date +%F)')
  "
  git add _data/topic_queue.yml
  git commit -m "daily-post: claim <topic-id>"
  git push origin master || echo "WARNING: push to master failed; see above." >&2
  ```

- **If it was discovered** (the queue was dry, so it has no queue entry), there is
  nothing to claim — `queue.py` exposes no way to add a new entry, only to transition
  an existing one (`claim()` looks the id up and raises `QueueError` when it is not
  found). Proceed straight to research. The same-day protection here comes from
  `run.sh` itself, not from the queue: once this run pushes
  `daily-post/$(date +%F)-<slug>` to `origin` in Stage 5, `run.sh`'s own precondition
  (`git ls-remote --heads origin "daily-post/$TODAY-*"`) stops a second invocation
  today before the skill is ever invoked again. Across a day boundary, the open-PR
  check above substantially mitigates a discovered candidate resurfacing: as long as
  this run's PR is still open, a later run finds it in `gh pr list` and rejects the
  rediscovered candidate the same way a `dupe_check` duplicate is rejected. What that
  check does not catch: a PR that has already merged (it is no longer "open", and
  `dupe_check`'s own `_posts/`-based view may not yet reflect it if the agent's local
  checkout is stale), and any day where the `gh pr list` call itself failed and was
  skipped. Neither is fully closed by a single run.

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

- Length, shape and tone per `references/voice.md` — that file is the single
  source for the word-count bound; do not restate it here, it will drift
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
that CI will reject. If it is still red after one fix, this run's own output was
broken, not the topic:

- **If the topic came from the queue**, return it to `queued` so a future run
  retries it, make that durable on `master`, and discard this run's draft:

  ```bash
  python3 -c "
  from pathlib import Path
  from script.daily_post.queue import mark
  mark(Path('_data/topic_queue.yml'), '<topic-id>', 'queued')
  "
  slug="<slug>"
  [[ -n "$slug" ]] || { echo "FATAL: slug is empty; refusing to clean up" >&2; exit 1; }
  [[ "$slug" =~ ^[a-z0-9-]+$ ]] \
    || { echo "FATAL: slug '$slug' is not a plain [a-z0-9-] slug; refusing to clean up" >&2; exit 1; }

  git add _data/topic_queue.yml
  git commit -m "daily-post: return <topic-id> to queued after preflight failure"
  git push origin master || echo "WARNING: push to master failed; see above." >&2

  # Keep the draft: exit 50 tells the operator to investigate, so the artifact
  # that makes investigating possible must survive the cleanup.
  mkdir -p ".git/daily-post-scratch/$(date +%F)"
  mv "_posts/$(date +%F)-$slug.md" \
     ".git/daily-post-scratch/$(date +%F)/failed-draft.md"
  echo "preflight failed; draft kept at .git/daily-post-scratch/$(date +%F)/failed-draft.md" >&2

  # `git clean` can only ever remove UNTRACKED files, so this cannot touch a
  # committed image no matter what $slug holds. Never use `rm -rf` on a path
  # built from a substituted value: an empty or stale slug would aim it at the
  # whole live image archive.
  #
  # No `-x`. The generated banner.webp/teaser.webp are untracked but NOT
  # gitignored, so plain `-fd` removes them. Adding `-x` would also delete
  # ignored files, and a slug that escaped the directory (`../..`) would then
  # reach .env, script/**/credentials.json and the rest of this repo's ignored
  # state. The shape check above is what makes that escape impossible; dropping
  # `-x` is what keeps the worst case survivable if it ever fails.
  git clean -fd -- "assets/images/$slug"
  echo preflight-failed > "$DAILY_POST_STATUS"
  ```

- **If the topic was discovered**, there is no queue entry to revert — just discard
  this run's draft:

  ```bash
  slug="<slug>"
  [[ -n "$slug" ]] || { echo "FATAL: slug is empty; refusing to clean up" >&2; exit 1; }
  [[ "$slug" =~ ^[a-z0-9-]+$ ]] \
    || { echo "FATAL: slug '$slug' is not a plain [a-z0-9-] slug; refusing to clean up" >&2; exit 1; }

  # Same rules as above: keep the draft for the operator, and remove generated
  # images with `git clean -fd` — untracked-only by construction, no `-x` so
  # ignored files (`.env`, credentials) are never in range — never `rm -rf`.
  mkdir -p ".git/daily-post-scratch/$(date +%F)"
  mv "_posts/$(date +%F)-$slug.md" \
     ".git/daily-post-scratch/$(date +%F)/failed-draft.md"
  echo "preflight failed; draft kept at .git/daily-post-scratch/$(date +%F)/failed-draft.md" >&2
  git clean -fd -- "assets/images/$slug"
  echo preflight-failed > "$DAILY_POST_STATUS"
  ```

No branch was ever created in this path — preflight runs before any checkout below —
so `master` is untouched apart from a queue-sourced topic's revert commit above, and
the tree is clean once the draft is moved aside and the generated images are cleaned.

**Once preflight is green**, the feature branch carries only the post and its
images — **never** `_data/topic_queue.yml`; that file's state is committed straight to
`master` instead, as described above. And **never write a terminal state before the
artifact that justifies it exists**: `published` is a claim about the world, and it
must wait until the PR that makes it true is actually open. (`claimed`, written early
in Stage 1, is different — it is not terminal, it is exactly what stops a same-topic
re-pick, and a stranded `claimed` topic is inspectable and recoverable; see the
operator note under "Failure handling".)

**Gates green:** branch, commit the post and its images only, push the branch, and
open the PR *first* — nothing below writes to `master` until the PR exists:

```bash
git checkout -b "daily-post/$(date +%F)-<slug>"
git add "_posts/$(date +%F)-<slug>.md" "assets/images/<slug>"
git commit -m "<post title>"
git push -u origin "daily-post/$(date +%F)-<slug>"
gh pr create --title "<post title>" --body "<summary + sources used>"
```

Only now that the PR exists, return to `master`, and — **if the topic came from the
queue** — mark it published there, commit, and push:

```bash
git checkout master
python3 -c "
from pathlib import Path
from script.daily_post.queue import mark
mark(Path('_data/topic_queue.yml'), '<topic-id>', 'published', slug='<slug>')
"
git add _data/topic_queue.yml
git commit -m "daily-post: publish <topic-id>"
git push origin master || echo "WARNING: push to master failed; see above." >&2
git branch -D "daily-post/$(date +%F)-<slug>" 2>/dev/null || true
echo published > "$DAILY_POST_STATUS"
```

**If the topic was discovered**, skip the `mark()`/commit/push above — there is no
queue entry for it — and just return to `master`, clean up the branch, and write the
status:

```bash
git checkout master
git branch -D "daily-post/$(date +%F)-<slug>" 2>/dev/null || true
echo published > "$DAILY_POST_STATUS"
```

This ordering matters: writing `published` to `master` before the PR exists would
leave a topic that can never be picked again (`next_queued()` only ever returns
`queued`) but has no PR and possibly no pushed branch to show for it — strictly worse
than a crash leaving the topic at its prior status.

The branch still lives on `origin` for the open PR; deleting only the local copy is
what keeps `run.sh`'s own `daily-post/<date>-*` idempotency check meaningful for a
genuine second run.

**Gates still blocked after two revision rounds:** the same ordering principle
applies — the draft PR must exist before anything here is treated as final. There is
no queue mutation to make durable on this path at all: **if the topic came from the
queue**, its `claimed` state is already durable on `master` from Stage 1, and nothing
between then and now changes it; **if it was discovered**, there was never a queue
entry to begin with. Either way, branch, commit the post and its images only, and
open the draft PR first:

```bash
git checkout -b "daily-post/$(date +%F)-<slug>"
git add "_posts/$(date +%F)-<slug>.md" "assets/images/<slug>"
git commit -m "<post title> [needs work]"
git push -u origin "daily-post/$(date +%F)-<slug>"
gh pr create --draft --title "<post title> [needs work]" \
  --body "<every gate's full verdict>"

# The label may not exist yet in this repo; `--force` makes creation idempotent
# (it creates or updates, and never fails because the label already exists).
# Neither call may sink an otherwise-good run: the draft PR is already open and
# already carries the full gate report, which is the part that matters.
gh label create needs-work --color FBCA04 --force \
  || echo "WARNING: could not create the needs-work label; continuing" >&2
gh pr edit --add-label needs-work \
  || echo "WARNING: could not label the draft PR needs-work; the PR is open and carries the gate report. Continuing." >&2
```

Only once the draft PR exists, return to a clean `master` and write the status,
exactly as on the green path:

```bash
git checkout master
git branch -D "daily-post/$(date +%F)-<slug>" 2>/dev/null || true
echo blocked > "$DAILY_POST_STATUS"
```

Leave a queue-sourced topic `claimed` in that case — it is neither published nor
rejected, and the operator decides which it becomes by reading the draft PR.

## Failure handling

Any unrecoverable error: write the closest matching token to `$DAILY_POST_STATUS`,
explain what happened in the transcript, and stop. Never leave the status file empty —
`run.sh` reports that as exit 50, which is indistinguishable from a crash.

Before stopping on any error, return the tree to a clean `master` the same way as the
paths above, in this order:

1. If `_data/topic_queue.yml` is still modified relative to `HEAD` (a claim or
   rejection that has not yet been committed), commit and push it directly to
   `master` using the non-fatal pattern above — never discard a dangling queue-file
   change, it is the durable record of what this run claimed or rejected.
2. Discard anything else this run touched (an untracked draft post, generated banner
   assets) with `git clean -fd -- <literal path>`, which by construction can only
   remove untracked files. Three rules, none optional: **no `-x`** (it would put
   ignored files — `.env`, `script/**/credentials.json` — in range); the path must be
   a **literal directory under `assets/images/`**, written out in full, never a value
   built from a substitution and never `.` or the repo root; and never `rm -rf` a path
   built from a substituted value.
3. `git checkout master`, then delete any local feature branch this run created
   (`git branch -D daily-post/$(date +%F)-<slug>`).
4. Write the status token.

Never leave `master` dirty or checked out on a feature branch — that silently breaks
tomorrow's run instead of failing loudly today.

**Operator note — a topic stranded `claimed`.** Because `claimed` is written early and
durably (Stage 1), a run that dies mid-flight after that point but before Stage 5
opens a PR can leave a queue-sourced topic sitting at `claimed` on `master` with no PR
to show for it. That run will have exited 50, so the operator is already alerted by
the exit code itself — this is not a silent state. Resolving it is a manual, one-line
edit: set the topic's `status` back to `queued` in `_data/topic_queue.yml` (commit and
push) to let a future run retry it, or leave it `claimed` deliberately if the work is
being picked up by hand.
