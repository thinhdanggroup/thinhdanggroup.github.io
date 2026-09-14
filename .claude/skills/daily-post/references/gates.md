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

Common knowledge in the field needs no ledger line. A specific number always does.

## Gate 2 — Duplicate

Stage 1 already compared titles. This gate compares *arguments*. Read the three
nearest posts `dupe_check.py` reported and answer: does this draft make a point one of
them already made?

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

Extract every code block. Syntax-check each one in its declared language. Run the
snippets that are runnable without network or credentials, in the scratch directory.

**Block on:** a block that does not parse; a runnable snippet that errors; code
calling an API that does not exist in the version the post names; a shell command that
would destroy data if pasted.

Pseudocode is allowed when labelled as such. Unlabelled pseudocode presented as real
code is a block.

## Gate 4 — Voice

Check the draft against `references/voice.md`.

**Block on:** any pattern in that file's "Hard blocks" section; a post outside
1,000–1,500 words; a missing worked example; a closing section that summarises without
concluding.

Do not block on dry humor or strong opinions — those are in-voice, and stripping them
produces exactly the prose this gate exists to prevent.

## After two failed rounds

Open a **draft** PR labeled `needs-work` whose body carries every gate's full verdict.
Write `blocked` to the status file. The work is preserved and the reason is legible;
nothing is silently discarded.
