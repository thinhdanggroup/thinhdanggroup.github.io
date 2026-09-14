# Daily Post Pipeline — Design

**Date:** 2026-09-14
**Status:** Approved for planning
**Scope:** A repo-local Claude Code skill plus supporting scripts that research, write,
review, and open a pull request for one blog post per run. Scheduling is explicitly out of
scope — the operator wires up their own trigger.

## Problem

Publishing daily to this blog by hand does not scale. The archive is 146 posts with real
search ranking, a strict front matter contract, and a consistent technical voice. Any
automation that lowers the bar damages an asset that took years to build.

The pipeline must therefore produce posts that are *indistinguishable in standard* from
hand-written ones, or refuse to publish and say why. Volume is worthless if the floor drops.

## Decisions

These were settled during brainstorming and are not open questions.

| Decision | Choice | Rationale |
| --- | --- | --- |
| Publish boundary | Open a PR; the human merges | Nothing reaches 146 ranked posts unreviewed |
| Topic source | Queue first, web discovery on empty queue | Control when the operator wants it, autonomy when they don't |
| Post length | 1,000–1,500 words | Sustainable daily; a deliberate lighter tier |
| Banners | Generated with Pillow | Only image toolchain actually present on the machine |
| Quality gates | Four, all hard blockers | Specified by the operator |
| Gate failure | Revise up to 2x, then draft PR labeled `needs-work` | Nothing is lost; failure is visible and diagnosable |
| Distribution | Out of scope | IndexNow/GSC/dev.to stay manual |
| Scheduling | Out of scope | Operator supplies the trigger |

## Architecture

The pipeline splits along one line: **anything mechanically checkable is a script with an
exit code; the model only judges what cannot be scripted.** Front matter validity, build
success, link integrity, and topic similarity are scripts. Truth, voice, and insight are
model judgment. This keeps the expensive, unreliable part of the system as small as possible
and makes most failures reproducible without a model in the loop.

```
script/daily_post/run.sh          entry point — the one line a trigger calls
  └── claude -p "/daily-post"     headless skill invocation
        ├── Stage 1  Select       topic_queue.yml → dupe_check.py
        ├── Stage 2  Research     WebSearch/WebFetch → research.md (evidence ledger)
        ├── Stage 3  Write        draft → _posts/YYYY-MM-DD-slug.md
        ├── Stage 4  Review       4 parallel gate subagents → verdicts
        │     └── revise (max 2 rounds) ──┘
        └── Stage 5  Publish      make_banner.py → preflight.sh → branch → gh pr create
```

### Layout

```
.claude/skills/daily-post/
    SKILL.md                 Pipeline definition: the 5 stages and their contracts
    references/
        voice.md             Voice rules extracted from the archive
        frontmatter.md       The contract check_frontmatter.py enforces
        sources.md           Research sources per beat
        gates.md             The 4 gate definitions and verdict schema
script/daily_post/
    run.sh                   Daily entry point; preconditions, logging, exit codes
    dupe_check.py            Similarity of a candidate against every existing post
    make_banner.py           Pillow → banner.webp (1600px) + teaser.webp (640px)
    preflight.sh             Front matter + jekyll build + htmlproofer, as CI runs them
_data/topic_queue.yml        Queued topics and the used-topic log (committed state)
```

The skill lives in the repo, not in `~/.claude/skills/`, because every rule it enforces is a
repo rule that changes when the repo changes. A skill versioned separately from the contract
it enforces drifts out of sync silently.

## Stage contracts

### Stage 1 — Select

Read `_data/topic_queue.yml`. Take the first entry whose `status` is `queued`. If the queue
holds none, discover a candidate by searching the beats listed in `references/sources.md`
(distributed systems, AI engineering, Python, infrastructure, databases, web development,
software engineering — the seven categories).

Run `dupe_check.py` on the candidate. It reads `_posts/*.md` directly — **not**
`blog_posts.json`, which carries only title, tags, and date, and goes stale whenever
`make generate` has not been run. The script compares the candidate title and angle against
each post's title, description, and H2 headings, and prints the five nearest matches with
scores.

**Blocks when** the top similarity score exceeds `0.55` (TF-IDF cosine over the combined
title, description, and headings text). That starting threshold is a constant at the top of
the script, to be tuned against the archive during implementation: it must flag
`2025-12-04-kafka-to-nats` as a near-duplicate of a hypothetical "migrating from Kafka to
NATS" candidate, while leaving genuinely distinct topics in the same category below the line.

On a block the run takes the next queue item, or discovers another candidate, up to three
attempts before exiting with a "no viable topic" status.

**Writes** `status: claimed` and the run date back to the queue entry, so a second run on the
same day cannot pick the same topic.

### Stage 2 — Research

Gather primary sources with WebSearch and WebFetch — specifications, release notes, source
code, benchmarks, and papers in preference to secondary commentary.

Produce `research.md` in the scratch directory as an **evidence ledger**: every claim the
post will make appears as a line carrying the claim, the source URL, and a verbatim quote
supporting it. This file is not a draft and is never published. It exists so that Stage 4 has
something to check against.

**The rule that makes the fact gate possible:** no claim may appear in the post unless it
appears in the ledger. Stage 3 writes from the ledger, not from model recall.

### Stage 3 — Write

Write to `_posts/YYYY-MM-DD-slug.md`, 1,000–1,500 words, following `references/voice.md` and
`references/frontmatter.md`.

Shape: one idea, one worked example, one takeaway. Problem, mechanism, worked example with
code, tradeoffs, verdict.

Front matter must satisfy the contract `script/check_frontmatter.py` enforces:

- `description` present, 50–200 characters
- at least one tag, reusing existing vocabulary where one fits
- exactly one category from the fixed seven
- `header.overlay_image` and `header.teaser` ending in `.webp` and existing on disk
- no code fence containing `{{` or `{%` outside a `{% raw %}` wrapper
- every `/assets/images/...` reference resolving to a real file

### Stage 4 — Review

Four gates run as **parallel subagents**, each returning a structured verdict
(`pass` | `block`, with findings carrying file and line). All four are hard blockers.

| Gate | Blocks on |
| --- | --- |
| **Fact trace** | Any non-obvious claim in the post with no corresponding line in `research.md` |
| **Duplicate** | Substantial overlap in argument with an existing post, beyond the title-level check in Stage 1 |
| **Code** | A code block that does not parse; an API that does not exist in the version the post names; a shell command that would destroy data if pasted. **Static analysis only — this gate never executes the draft's code** (see `references/gates.md`): the pipeline runs unattended in a working directory holding push rights, so running model-written code there is never worth what it would catch. The earlier "runnable snippet that fails in a sandbox where one is feasible" wording is superseded; no sandbox was feasible, and "where feasible" degraded to running it in the repo. |
| **Voice** | Hedging, listicle padding, filler openings, and the other tells enumerated in `references/voice.md` |

On any block, the findings go back to Stage 3 and the post is revised. **Maximum two revision
rounds.** The cap is deliberate: a draft rewritten repeatedly against a voice gate converges
on blandness, which is the failure mode the gate exists to prevent.

### Stage 5 — Publish

1. `make_banner.py` renders the banner from the post title and category — typography over a
   category-tinted gradient — writing `banner.webp` at 1600px and `teaser.webp` at 640px into
   `assets/images/<slug>/`.
2. `preflight.sh` runs `check_frontmatter.py`, `bundle exec jekyll build`, and htmlproofer
   with the same flags CI uses. A red preflight is a hard stop — the pipeline never pushes a
   branch it knows CI will reject.
3. Commit to a `daily-post/<date>-<slug>` branch, push, and open a PR with `gh`.

**Green after review** → a normal PR.
**Still blocked after two revisions** → a **draft** PR labeled `needs-work`, whose body
carries the full gate report. The work is preserved and the reason is legible.

## Unattended operation

The pipeline runs with no human present, which imposes three constraints.

**No interactive prompts.** The skill never asks a question. Every decision resolves from
`_data/topic_queue.yml` or the gate rules. A pipeline that blocks on a question a human is
not there to answer has hung, not paused.

**Idempotent per day.** `run.sh` exits early if a post for today's date already exists in
`_posts/`, or if a `daily-post/*` branch for today is already open. This protects against a
double-fire and against a manual run landing on top of an automated one.

**Preconditions checked up front.** `run.sh` verifies `gh` is installed and authenticated,
the working tree is clean, and `master` is current — before any expensive work. `gh` is
**not currently installed on this machine**; the operator must install and authenticate it.
Failing at the last step after a full research-and-write cycle wastes the whole run.

Exit codes distinguish the outcomes a trigger cares about, so a cron wrapper can alert on
some and ignore others:

| Code | Meaning | Operator action |
| --- | --- | --- |
| `0` | Post written, gates green, PR open | Review and merge |
| `10` | Gates still blocked after two revisions; draft PR open | Read the gate report |
| `20` | No viable topic after three attempts | Stock the queue |
| `30` | Already ran today; nothing done | None — expected on a double-fire |
| `40` | Precondition failed (`gh` missing, dirty tree, stale `master`) | Fix the environment |
| `50` | Preflight red — build or front matter broken | Investigate; a bug in the pipeline |

## Dependencies

Verified present: Pillow (WebP output), Inter and JetBrains Mono fonts, Ruby/Jekyll toolchain
via `make install`, Python 3.12.

Verified absent: `gh` (**required**, must be installed), `cairosvg`, `rsvg-convert`,
ImageMagick, `cwebp` — none needed, since banner rendering goes through Pillow alone.

Font availability differs across machines. `make_banner.py` falls back to DejaVu when Inter
is missing, and the font file may be vendored into the repo if identical output across
environments matters.

## Risks

**Daily cadence against four hard gates will fail on some days.** This is the specification
working, not a defect. The observable symptom is a `needs-work` draft PR instead of a
mergeable one. The lever, if the rate proves too high in practice, is demoting the voice gate
from blocker to warning — a one-line change in `references/gates.md`.

**Topic discovery quality is the weakest link.** An empty queue puts topic selection entirely
in the model's hands, and a mediocre topic passes all four gates — none of them measure
whether anyone wanted to read it. Keeping the queue stocked is the mitigation.

**Cost per run is substantial**: research, writing, four review subagents, and up to two
revision rounds.

## Out of scope

Scheduling and triggering. Distribution to IndexNow, Google Search Console, and dev.to.
Image art beyond the generated banner. Editing or refreshing existing posts.
