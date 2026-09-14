# Quality gates

Four gates run as parallel subagents after the draft is written. **All four are hard
blockers.** Each returns a verdict; any `block` sends the findings back to the writer.

**At most two revision rounds.** The cap is deliberate: a draft rewritten repeatedly
against a voice gate converges on blandness, which is the failure mode the gate exists
to prevent. After the second failed round, stop and open a draft PR.

## Verdict schema

Each gate subagent returns exactly this JSON and nothing else:

```json
{
  "gate": "fact | duplicate | code | voice",
  "verdict": "pass | block",
  "findings": [
    {"location": "line 42 or a quoted phrase", "problem": "what is wrong", "fix": "what to do"}
  ]
}
```

An empty `findings` array with `"verdict": "block"` is itself a failure — a blocking
gate must say what to fix.

## Gate 1 — Fact trace

Read the draft and `research.md` side by side. For every non-obvious claim in the
draft — a number, a behaviour, a version, an API, a guarantee — find the ledger line
supporting it.

**Block on:** any such claim with no ledger line; any claim whose ledger quote does not
actually support it; any citation link that does not resolve.

Common knowledge in the field needs no ledger line. A specific number always does —
and so does any behavioural claim about a named product, version, or API, even when
it has no number in it. "TCP retransmits lost segments" is common knowledge and needs
no ledger line. "JetStream acknowledges a publish before the replica set has fsynced"
names a specific system and describes specific behaviour of it, so it always needs
one, exactly like a number would. Do not stretch "common knowledge" to cover a claim
just because it happens to lack a digit — the test is whether the claim is a general,
textbook fact anyone in the field would state the same way, not whether it is
numeric.

## Gate 2 — Duplicate

Stage 1 already compared titles. This gate compares *arguments*. Read the three
nearest posts `dupe_check.py` reported, the draft, and `research.md` (the evidence
ledger — see `sources.md`), and answer: does this draft make a point one of the three
nearest posts already made? The ledger is a useful cross-check here: the same primary
source turning up for two posts is not proof of duplication by itself, but it is a
prompt to read both arguments closely rather than trust the mechanical score.

**This gate is the semantic backstop for a mechanical check with weak recall, and it
must judge on argument overlap regardless of what the mechanical score was.** When
`dupe_check.py`'s TF-IDF cosine score was measured against the live archive, three of
seven ordinary rewordings of a single real topic scored below the 0.55 threshold and
would have passed as "viable" on the number alone:

| Candidate title (all the same underlying topic) | Mechanical score | Mechanical verdict |
| --- | --- | --- |
| "Migrating from Kafka to NATS" | 0.599 | duplicate |
| "Moving off Kafka onto NATS" | 0.489 | **passed** |
| "Replacing our message broker: Kafka to NATS" | 0.377 | **passed** |
| "Why we switched messaging systems from Kafka" | 0.328 | **passed** |

A low mechanical score is **not evidence that the topic is fresh** — it frequently just
means the wording differs while the argument is identical. Do not defer to the number,
and do not treat a "passed" mechanical verdict as a reason to skip or soften this gate's
own reading of the three nearest posts. Read them in full and compare what each one
actually argues.

**Block on:** the draft's central argument substantially restating an existing post,
irrespective of how dissimilar the title or wording looks and irrespective of the
mechanical score. A new post on a covered topic is fine when it makes a genuinely
different point — say so explicitly in the verdict, naming the prior post and the
specific way the argument differs.

## Gate 3 — Code

**This gate never executes the draft's code. Static analysis only.** No snippet from
the post is run, sourced, imported, evaluated, piped into an interpreter, or executed
in any other form — not in the scratch directory, not in `/tmp`, not anywhere, not
even when it "looks harmless" or "obviously has no side effects". This is not a
default to be relaxed under time pressure or by a future editor tidying the gate up:
the pipeline runs unattended with a working directory that holds push rights and
credentials, so running code the model just wrote is the one action this gate must
never take. A gate that cannot check something without executing it reports that
limitation in its findings and moves on.

Extract every code block and check each one **statically**:

1. **Parse it in its declared language.** Parse-only checkers are the tool here,
   because they read the source without running it — `bash -n <file>` for shell,
   `python3 -m py_compile <file>` for Python, `node --check <file>` for JavaScript,
   the equivalent parse/typecheck-only mode for anything else. These are permitted
   precisely because they never execute the snippet; anything that *interprets* the
   snippet (`bash <file>`, `python3 <file>`, `node <file>`, `eval`, a REPL, a test
   runner) is forbidden regardless of what it would tell you.
2. **Check every API against the version the post names**, by reading the
   documentation for that version — not by calling the API.
3. **Read every shell command as if it were about to be pasted into a terminal**, and
   judge the damage it would do there.

**Block on:** a block that does not parse; code calling an API that does not exist in
the version the post names; a shell command that would destroy data if pasted (an
unguarded `rm -rf` on a substituted or relative path, a force-push, a `DROP`/`DELETE`
without a `WHERE`, a `dd` onto a device).

Pseudocode is allowed when labelled as such. Unlabelled pseudocode presented as real
code is a block.

**Diagrams are checked here too, and statically, by the same rule.** A Mermaid
block is source that a browser parses, and a block Mermaid cannot parse ships as a
visible red error box where the diagram should be — the Jekyll build succeeds and
htmlproofer sees a perfectly good `<pre><code>`, so nothing else in the pipeline
notices. The check is already written and already runs:

```bash
python3 script/check_frontmatter.py
```

`preflight.sh` runs it in Stage 5 and CI runs it on every push, so this gate does not
need to invoke anything new — it needs to read that output and treat a Mermaid finding
as a block like any other. It validates every ```` ```mermaid ```` fence structurally:
non-empty, a first real line declaring a diagram type Mermaid 10.6.1 actually supports,
no tab characters (the parser is whitespace-sensitive), and no Liquid (Jekyll would eat
it first). It deliberately does **not** shell out to `mermaid-cli`, because that would
put `node` on the pipeline's critical path — a tool being installed but not on `PATH`
is exactly how bundler turned a good post into a false failure.

**Block on:** any Mermaid finding from that script.

Because nothing is executed, this gate cannot catch a runtime error in an
otherwise-parsing snippet. That is the deliberate trade: an uncaught runtime bug in a
published example costs a correction, and executing model-written code inside a repo
with push rights costs considerably more.

## Gate 4 — Voice

Check the draft against `references/voice.md`.

### Length

`voice.md` owns the word-count range **and** the definition of what counts toward it
(its "What counts toward the word count" section). Do not restate either here and do
not invent a counting rule of your own — an unstated convention is how one run ends up
compressing prose another run would have passed.

Measure it mechanically, so two runs cannot disagree. This counter implements
`voice.md`'s definition exactly: front matter dropped, fenced code blocks dropped,
everything from the closing link-list heading onward dropped.

````bash
python3 - "_posts/<date>-<slug>.md" <<'COUNT'
import sys

CLOSING = {"further reading", "further reading & references", "references"}
lines = open(sys.argv[1], encoding="utf-8").read().splitlines()

i = 0
if lines and lines[0].strip() == "---":              # YAML front matter
    i = 1
    while i < len(lines) and lines[i].strip() != "---":
        i += 1
    i += 1

words, in_code = 0, False
for line in lines[i:]:
    s = line.strip()
    if s.startswith("```") or s.startswith("~~~"):    # fenced code block
        in_code = not in_code
        continue
    if in_code:
        continue
    if s.startswith("#") and s.lstrip("#").strip().lower() in CLOSING:
        break                                        # the closing link list
    words += len(line.split())
print(words)
COUNT
````

Report that number in the verdict, passing or blocking, so the writer never has to
guess which rule was applied. A draft already inside the range is in range: **do not
ask for compression that only moves it around inside the bound.**

### Diagrams

`voice.md`'s "Diagrams" section owns the rule; this gate applies it in both directions.

**Block on a warranted diagram that is absent:** the post's central mechanism is an
interaction ordered across two or more components, or a state machine, and the draft
describes it only in prose. That is the case `voice.md` says a diagram is for — the
reader is being asked to rebuild a timeline in their head from a serial description.

**Escape clause, and it is not optional.** When the mechanism is genuinely single-actor
and linear — one component, no handoff, no concurrency, no branching — prose is the
correct form and the absence of a diagram is **not a finding**. The same goes for a
comparison a table already carries, and for a concept with no ordering or state at all.
Do not reach for this block because a post merely *could* have a picture; demanding
filler diagrams is the same "converges on blandness" failure this file warns about at
the top, just drawn in boxes and arrows. Say in the verdict which shape you judged the
mechanism to be, so the writer can disagree with the judgement rather than the demand.

**Block on a diagram that is present but decorative** for exactly the same reason: it
costs the reader attention and returns nothing.

**Do not block on the diagram's syntax** — Gate 3 owns that, mechanically.

**Block on:** any pattern in `voice.md`'s "Hard blocks" section; a prose-word count
outside the range `voice.md` sets, measured as above; a missing worked example; a
closing section that summarises without concluding; a warranted diagram that is
absent, subject to the escape clause above.

Do not block on dry humor or strong opinions — those are in-voice, and stripping them
produces exactly the prose this gate exists to prevent.

## After two failed rounds

Open a **draft** PR labeled `needs-work` whose body carries every gate's full verdict.
Write `blocked` to the status file. The work is preserved and the reason is legible;
nothing is silently discarded.
