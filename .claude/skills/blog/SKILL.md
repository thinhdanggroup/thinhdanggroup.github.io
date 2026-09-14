---
name: blog
description: Run the whole daily blog-post pipeline end to end via script/daily_post/run.sh — preconditions, lock, timeout and exit-code contract, exactly as a scheduler would — then explain the outcome in plain language. Use this when a person asks for a post ("write today's post", "/blog", "run the blog pipeline", "publish a post"). The `daily-post` skill is the five-stage pipeline itself and is what run.sh invokes; this one drives it and reports back.
---

# /blog

One command that runs the blog pipeline the way cron would, then explains what
happened. `run.sh` owns the preconditions, the lock, the timeout and the exit
codes — do not reimplement any of them, and do not invoke `/daily-post` directly
instead: that skips every mechanical guard (idempotency, the concurrency lock,
the publish-boundary check) the unattended design depends on.

The five stages live in the `daily-post` skill
(`.claude/skills/daily-post/SKILL.md`). Read that only if you need to explain
*what* a stage did; you do not need it to run the pipeline.

## Run it

```bash
export PATH="$(ruby -e 'print Gem.user_dir')/bin:$PATH"
cd <repo root>
script/daily_post/run.sh; echo "run.sh exit: $?"
```

**The `export PATH` line is not optional.** `bundle` installs into the *user gem
directory*. An interactive shell puts that on `PATH`; a scheduler — and this
skill's own shell — does not. Without it `preflight.sh` reports "bundler not
found", the run fails its checks, and the failure looks like a broken post
rather than a broken machine. This is the single most common way this pipeline
fails on a new machine.

Capture the exit code on the same line as the invocation, as above. `run.sh`
prints its own log to stdout *and* to `.git/daily-post-logs/<today>.log`; the
exit code is the part that tells you what to say.

A full run takes minutes, not seconds — `DAILY_POST_TIMEOUT` defaults to 3600s.
Let it finish.

## Exit codes

Taken from `script/daily_post/run.sh`'s own header, which is authoritative. If
this table and that header ever disagree, the header wins and this file is the
bug.

| Code | Meaning | What to tell the person |
| --- | --- | --- |
| `0` | Post written, gates green, PR open | A post is ready. Give them the PR link and the title. **They merge it**, not you. |
| `10` | Gates still blocked after two revision rounds; draft PR open, labeled `needs-work` | **This is the pipeline working.** Read the draft PR's body for the gate report, then say *which* gate blocked (fact, duplicate, code, or voice) and *why*, in their words — not "it failed". They decide: fix the draft on the branch, or close it. |
| `20` | No viable topic after three attempts | The topic queue is dry or everything in it duplicates a published post. Point them at `_data/topic_queue.yml` to add topics. Nothing was written; nothing is broken. |
| `30` | Already ran today — a post or a `daily-post/<today>-*` branch already exists, locally or on origin | Benign. Nothing was done because something for today already exists. Say so and stop. |
| `31` | Another run currently holds `.git/daily-post.lock` | Nothing was done. If it happens once, a run is genuinely in flight — wait. **If it repeats, a previous run hung and is still holding the lock**, which silently stops every future run: check `.git/daily-post-logs/` and kill the stuck process. Never confuse this with `30`. |
| `40` | Precondition failed | The machine is not ready; the pipeline never started. The log's `PRECONDITION FAILED:` line names the exact cause — a missing `git`/`claude`/`gh`/`python3`/`flock`/`timeout`, not a git repository, `gh` unauthenticated, `master` not checked out, a dirty working tree, `master` not fast-forwardable, `ruamel.yaml` missing, the log directory not creatable, or the lock file unopenable. Quote that line, then point at **`README.md` → "Before the first run"** for the fix. |
| `50` | Pipeline failure: preflight was red, or the skill reported no status | Something broke. On a preflight `2` the *environment* is broken rather than the post, and the draft plus the topic's `claimed` state are deliberately preserved — say that, so they investigate the machine instead of rewriting good prose. The log is the evidence; read it before summarising. |
| `60` | The skill exceeded `DAILY_POST_TIMEOUT` (default 3600s) and was killed | The run hung and was killed at the timeout. Deliberately never reported as `30`: a hung run must not claim "nothing to do". Read the log to see which stage it died in. |
| `70` | Publish-boundary violation: files other than `_data/topic_queue.yml` landed on local `master` | Serious. Post content is supposed to reach `master` only through a reviewed PR. The log lists the offending files. `run.sh` pushes nothing itself, but the skill pushes queue state during Stages 1 and 5 — tell them to check `origin/master` as well as local `master` (`git log <before>..master`) before resetting anything. Do not reset it for them. |
| `71` | The run finished with an unclean working tree | The skill left uncommitted changes behind; they are left in place on purpose, for inspection. Show them `git status`. Until it is resolved, tomorrow's run fails its precondition as exit `40` — a day away from the run that caused it, which is why it is caught here. A `preflight.sh` exit `2` commonly reaches the operator this way: the draft is deliberately kept, so the tree is deliberately dirty. |

## After the run

Say, in plain language and in this order:

1. what the exit code means for them;
2. the PR link and title, on `0` or `10`;
3. on `10`, which gate blocked and why, read out of the PR body — this is the
   whole value of a `10`, and "the gates blocked" on its own is not an answer;
4. what they should do next, if anything.

Do not paste the raw log. Quote at most the one or two lines that carry the
cause.

## What not to do

- **Do not re-run after a `10`.** A second run picks a *different* topic; it
  does not fix the blocked draft. The draft PR is the deliverable — it is
  labeled `needs-work` so a human can act on it. Re-running buries it.
- **Do not fix a `40` by weakening `run.sh`'s preconditions.** They exist
  because this normally runs unattended, where a wrong assumption becomes a
  silent bad push rather than a visible error. Fix the machine, using
  `README.md` → "Before the first run".
- **Do not push or merge the PR.** A human merging is the point of the design,
  not an oversight in it. The same goes for `--dangerously-skip-permissions`:
  an unattended run with push rights is exactly the configuration the
  permission allowlist exists to prevent.
- **Do not run `/daily-post` directly to "skip the wrapper".** That bypasses the
  lock, the idempotency check and the publish-boundary assertion.
- **Do not clear `.git/daily-post.lock` by hand on a `31`** without first
  finding out whether a run is still alive. Deleting a live run's lock is how
  two pipelines end up in the same working tree.
