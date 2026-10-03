---
title: "pstack Turns Off Skill Auto-Loading for 46 of Its 47 Skills"
description: "How Cursor's pstack plugin swaps description-matched skill loading for one router, three fan-out skills with different merge rules, and checker scripts."
tags:
    - AI Agents
    - Developer Tools
    - LLM
categories:
    - ai-engineering
header:
    overlay_image: /assets/images/pstack-skill-router/banner.webp
    overlay_filter: 0.5
    teaser: /assets/images/pstack-skill-router/teaser.webp
toc: true
toc_sticky: true
---

You install a pack of forty-odd agent skills, type "check on PR 123", and two of them light up. One is the pack's carefully written PR-babysitting playbook. The other is the editor's built-in skill with a description that happens to match the same words. The agent picks one. You find out which by reading the transcript afterwards.

[pstack](https://github.com/cursor/plugins/tree/main/pstack), Lauren Tan's Cursor plugin (version 0.15.5, MIT), runs into exactly this collision and writes it down. Its router says PR-status requests go to its own Babysit playbook "and not Cursor's built-in babysit skill, whose description matches the same words." The more interesting thing is the design decision behind that line. pstack mostly stops letting the agent choose skills by description at all.

## Forty-six of forty-seven skills opt out of being picked

Cursor's skill model is relevance by description: "The agent is presented with available skills and decides when they are relevant based on context." The escape hatch is one frontmatter field, `disable-model-invocation: true`, which makes a skill "behave like a traditional slash command, where it is only included in context when you explicitly type `/skill-name` in chat."

You can count how pstack uses it. On the checkout I read (commit `7022c81`):

```bash
# Run from the root of a cursor/plugins checkout.
cd pstack
echo "skills: $(ls -d skills/*/ | wc -l)"
echo "manual-only: $(grep -l '^disable-model-invocation: true' skills/*/SKILL.md | wc -l)"
echo "auto-loadable:"
grep -L '^disable-model-invocation: true' skills/*/SKILL.md
```

That prints 47 skills, 46 manual-only, and exactly one auto-loadable file — `skills/setup-pstack/SKILL.md`, the installer that writes the model config. Everything else, including the twenty-three single-principle skills and the router itself, is invisible to description matching.

Run the same block on your own skill pack. If everything auto-loads, routing is the agent's judgment over names and one-line descriptions, and every new skill is another chance at a babysit-style collision.

## One router does the picking instead

The replacement is `poteto-mode`, a 2,749-word SKILL.md that the README calls "a sticky mode: once entered it stays on across turns." It does three jobs that description matching cannot.

**It maps situations to skills explicitly.** The top of the file is a trigger table written as arrows: "Contested design → the **interrogate** skill (multi-model adversarial) before shipping." "Before review → the **no-comments** skill." Parallel fan-out goes to **swarm**, and design bakeoffs go to **arena**. Each arrow is a decision made once by the author, not re-guessed by the agent from description text on every prompt.

**It indexes the principles inline and makes reading them checkable.** All twenty-three principles appear in the router as one-line entries, each naming when it applies. **Attack the Premise**, for example, applies when "Two or more fixes that share one premise have failed the same gate." The full rule lives in a leaf skill the agent must open: "Read the leaf skill in full for any principle you apply." Then comes the line I would steal first: "Cite only principles whose leaf SKILL.md you read this session." A citation without a read is a violation you can spot in the transcript.

**It turns playbooks into a todo list the agent cannot quietly shorten.** There are twenty-three playbooks (bug fix, perf, babysit, shipping, autonomous run and so on). The router's rule: "Open a todolist whose first items are the matched playbook's steps, copied in verbatim." A step the agent decides to skip "stays in the list with a one-line `skip: <reason>`." Skipping is allowed. Skipping silently is not.

## I tested the router against description matching

**The short version: without a router, the agent picked the wrong skill in 89 of 90 trials, and the router made it pick the right one every time.**

Two skills both claim "check on PR 123. anything outstanding?". `pr-status` plays the editor's built-in, the one we don't want. `babysit` plays the pack's own skill, the one we do want, and its description nearly repeats the user's words. Each skill only prints its own name, so the reply shows which one ran. I used Claude Code, which defines the flag the same way as Cursor.

```bash
cd "$(mktemp -d)"  # empty dir, so no other project skills load
mkdir -p .claude/skills/pr-status .claude/skills/babysit
cat > .claude/skills/pr-status/SKILL.md <<'EOF'
---
name: pr-status
description: "Check on a pull request: CI status, review comments, merge conflicts, anything outstanding on a PR."
---
Your entire reply must be exactly this one line: ROUTED: pr-status
EOF
cat > .claude/skills/babysit/SKILL.md <<'EOF'
---
name: babysit
description: "Use for 'check on PR X', 'anything outstanding on X', 'babysit this', 'get it green'. Drives a PR to merge-ready."
---
Your entire reply must be exactly this one line: ROUTED: babysit
EOF

# One trial. --setting-sources project keeps user-level skills and plugins out.
claude -p "check on PR 123. anything outstanding?" --model sonnet \
  --setting-sources project --no-session-persistence --max-turns 6 \
  --disallowedTools "Bash Edit Write WebFetch WebSearch Agent NotebookEdit" \
  --output-format json | jq -r .result
```

I ran four setups. **A** changes nothing. **B** hides `babysit` with `disable-model-invocation: true` and adds no router. **C** hides `babysit` and adds a manual-only `pack-mode` router, invoked as `/pack-mode check on PR 123. anything outstanding?`, whose one trigger says to read `.claude/skills/babysit/SKILL.md` with the Read tool and follow it exactly: "Do not use the pr-status skill, whose description matches the same words." **D** is a control, A with the two descriptions swapped. Ten trials per setup per model, on Claude Code 2.1.288:

| Setup | Sonnet | Haiku | Opus |
| --- | --- | --- | --- |
| A. Both skills auto-load | pr-status 10/10 | pr-status 10/10 | pr-status 10/10 |
| B. `babysit` manual-only, no router | pr-status 10/10 | pr-status 10/10 | pr-status 10/10 |
| C. Router with an explicit trigger | babysit 10/10 | babysit 10/10 | babysit 10/10 |
| D. A, with the two descriptions swapped | pr-status 10/10 | pr-status 10/10 | pr-status 9/10 |

Setups A and C, traced:

<iframe src="/assets/htmls/pstack-skill-routing.html" title="Skill routing, setups A and C" loading="lazy" style="width:100%;height:460px;border:1px solid #ddd;border-radius:8px"></iframe>

[Open full size](/assets/htmls/pstack-skill-routing.html)

**A: the pack's skill never won,** even though its description nearly repeated the request.

**D says why.** With the descriptions swapped, `pr-status` still won 29 of 30. The description was not driving the choice. My guess is the name, since `pr-status` sounds like "check on PR". Either way, a better description would not have rescued `babysit`.

**B: hiding a skill is not routing.** The flag only takes `babysit` out of the contest, so `pr-status` wins by default.

**C: only an explicit rule fixed it**, 10 of 10 on every model.

Sonnet's per-trial cost was identical after trial one in every setup, so its ten trials are one answer repeated, not a rate. It is a toy fixture in Claude Code, not Cursor, and all 120 trials cost $1.18.

## Three fan-out skills that differ only after the agents return

`interrogate`, `arena` and `swarm` all spawn agents in one message, with models from one config file. They differ in how they merge results.

| Skill | Who runs | What comes back | Merge rule |
| --- | --- | --- | --- |
| `interrogate` | One read-only reviewer per model, same prompt | Findings on a diff | Findings from 2+ models are "highest signal"; nothing is auto-applied |
| `arena` | N candidates; the rubric is hidden from them | Competing artifacts | A cross-judge scores them; the parent picks a base and grafts by hand |
| `swarm` | N cloud workers on slices or races | `PASS`, `ISSUES` or `BLOCKED` | The race rule is declared before spawning; "a gap does not count as a pass" |

The models come from `~/.cursor/rules/pstack-models.mdc`, which `/setup-pstack` writes. For panel roles "the list length sets the count", so a fourth model on its `interrogate reviewers` line is a fourth reviewer.

## Rules the agent kept breaking became scripts

pstack's principle **encode lessons in structure** says to turn a repeated correction into "a lint, metadata flag, runtime check, or script instead of more text", because "agents copy whatever the surrounding code already does and a weaker guard becomes the next template." The plugin follows it in at least two places, and I ran both against bad input.

`check-plan.mjs` validates a multi-PR plan before it reaches a human. It fails the file on long dashes, curly quotes and mid-sentence colons — the router's reply rules ban the first and the last as well — and on structure: every PR section needs the sub-blocks `Depends on.` through `Merge.` in order, and its live-verification block needs lanes numbered 1 to 10, each naming a screenshot and a pass predicate. Fed a three-line plan with one long dash and one mid-sentence colon, it printed six problems, each with `file:line`, and exited 1. Step 6 of the multi-phase-plan playbook is "fix every line it prints".

`log.sh` is the helper behind **show-me-your-work**, a TSV decision log for unattended runs. Its non-obvious job is security: it prefixes any cell starting with `=`, `+`, `-` or `@` with a quote, because the log gets opened in spreadsheets and its evidence column holds PR titles and generated text. An evidence cell of `=HYPERLINK(...)` came out as `'=HYPERLINK(...)`. So did `-1 regressions`, which a spreadsheet would now read as text, not a number. That is the right trade for an audit log, but it is a trade.

## What it costs

A 2,749-word router is a fixed context cost before any work happens. Manual-only skills mean nothing fires unless you invoke the router, so a session where you forget `/poteto-mode` gets none of it. And the router is one person's taste, made executable; pstack's `/automate-me` drafts your own router.

If you maintain a skill pack, the takeaway is concrete. Count how many of your skills auto-load. Keep that set to the ones a user would ask for by name before anything else is running, move the rest behind one router with explicit triggers, and every time you correct the agent twice for the same thing, write the check instead of the third sentence.

## Further reading

- [pstack README — cursor/plugins](https://github.com/cursor/plugins/tree/main/pstack)
- [pstack `poteto-mode` router skill](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/SKILL.md)
- [pstack `interrogate` skill](https://github.com/cursor/plugins/blob/main/pstack/skills/interrogate/SKILL.md)
- [pstack `arena` skill](https://github.com/cursor/plugins/blob/main/pstack/skills/arena/SKILL.md)
- [pstack `swarm` skill](https://github.com/cursor/plugins/blob/main/pstack/skills/swarm/SKILL.md)
- [pstack `setup-pstack` skill](https://github.com/cursor/plugins/blob/main/pstack/skills/setup-pstack/SKILL.md)
- [pstack `check-plan.mjs`](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/scripts/check-plan.mjs)
- [pstack `show-me-your-work` `log.sh`](https://github.com/cursor/plugins/blob/main/pstack/skills/show-me-your-work/scripts/log.sh)
- [pstack principle: encode lessons in structure](https://github.com/cursor/plugins/blob/main/pstack/skills/principle-encode-lessons-in-structure/SKILL.md)
- [Cursor docs: Agent Skills](https://cursor.com/docs/context/skills)
- [Claude Code docs: Skills](https://code.claude.com/docs/en/skills)
