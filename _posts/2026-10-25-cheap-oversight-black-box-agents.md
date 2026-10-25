---
title: "Cheap Oversight for Black-Box Agents"
description: "Judgment-based monitors score one action at a time and miss loops and cost blowups by design — circuit breakers and OS-enforced sandboxes catch what scoring can't."
tags:
    - AI Agents
    - Security
    - LLM
categories:
    - ai-engineering
header:
    overlay_image: /assets/images/cheap-oversight-black-box-agents/banner.webp
    overlay_filter: 0.5
    teaser: /assets/images/cheap-oversight-black-box-agents/teaser.webp
toc: true
toc_sticky: true
---

Your monitor scores every tool call before it runs. 3, 2, 4, 1, 3 — nothing trips the threshold. Forty minutes later the agent has made six thousand of those calls, burned through the month's inference budget, and not one of them was flagged, because no individual call was wrong. The agent was stuck in a loop, politely re-reading the same file and re-asking the same question, and a monitor built to judge actions one at a time has no way to see a loop. The failure isn't in any single decision. It's in the aggregate, and aggregates are exactly what a per-action scorer cannot see.

That's the gap a judgment-based monitor — whether it's a hand-rolled prompt, a trained classifier, or a frontier model acting as judge — leaves open by construction. It can be cheap, it can be accurate on the cases it's built to catch, and it will still miss the failure modes that live in the sequence rather than the step: a cost blowup, an infinite retry, a command that is individually fine but collectively does something nobody approved. Catching those doesn't take a smarter judge. It takes a layer that doesn't try to judge anything at all.

## The blind spot in judging actions one at a time

A per-action monitor's job is to answer "is this action okay?" for one action, in isolation, every time it's asked. That framing is precisely what makes it cheap — no state, no memory of the last thousand calls, just a score. It's also why a loop is invisible to it: every iteration looks identical to the one before, and identical to a one-off call that would also pass. There is no "this is the four-thousandth time you've asked this" in the scoring function, because the scoring function doesn't carry a count.

The OpenAI Agents SDK's own guardrail mechanism has the same shape, for the same reason. A guardrail function returns a result, and the runner checks a single field on it — `tripwire_triggered` — before deciding whether to raise `InputGuardrailTripwireTriggered` or `OutputGuardrailTripwireTriggered` and halt. That's a judgment about one input or one output. Output guardrails specifically run only after the agent has already produced its final response for that turn, so even a correct verdict arrives after the work is done, not before it. None of this is a flaw in the design — it's doing exactly what a per-turn check is for. It just isn't the layer that catches a hundred correct turns in a row adding up to an incident.

## A circuit breaker doesn't need to understand anything

The fix for an aggregate failure is an aggregate bound, and the cheapest one is a circuit breaker: a counter that doesn't ask whether any action was good or bad, only how many have happened and how much they've cost.

The Agents SDK already ships half of this. `Runner.run` takes a `max_turns` argument — where a turn is one model invocation, tool calls included — and it defaults to a built-in ceiling (`DEFAULT_MAX_TURNS`), so the breaker is on unless you remove it. Once the count is exceeded, it raises `MaxTurnsExceeded` unless you catch it. The thing worth noticing is the failure direction: passing `None` disables the limit entirely, which means the protection is one keyword argument away from silently not existing — not a default you forgot to add, but one you can accidentally delete.

`max_turns` bounds turn count, not spend, and a turn with ten parallel tool calls costs very differently from a turn with one. The gap is easy to close with the same shape of check — no model call, just arithmetic against a running total:

```python
from dataclasses import dataclass, field
from agents import Agent, Runner, RunContextWrapper


class BudgetExceeded(Exception):
    """Raised when cumulative token spend crosses the configured ceiling."""


@dataclass
class SpendTracker:
    max_tokens: int
    spent: int = field(default=0)

    def record(self, usage_tokens: int) -> None:
        self.spent += usage_tokens
        if self.spent > self.max_tokens:
            raise BudgetExceeded(
                f"spent {self.spent} tokens, ceiling is {self.max_tokens}"
            )


async def run_with_budget(agent: Agent, prompt: str, max_tokens: int = 50_000):
    tracker = SpendTracker(max_tokens=max_tokens)
    result = await Runner.run(agent, prompt, max_turns=25)
    # result.raw_responses carries per-turn usage; tally it against the ceiling
    for response in result.raw_responses:
        tracker.record(response.usage.total_tokens)
    return result
```

This check costs nothing to run — it's a comparison, not an inference call — and it catches the exact case the cold open describes: six thousand individually-fine tool calls that never should have added up to six thousand. A per-action monitor scoring each of those calls would do six thousand units of work and still say nothing was wrong, because nothing was, one at a time. The circuit breaker does one comparison and stops the run.

## Bounding what a single action can do

A circuit breaker answers "how much happened." It says nothing about "what could one action have done," and that's a separate question a counter can't close. For that, the bound has to sit underneath the agent entirely, at the level the operating system enforces rather than the level the model reasons at.

Claude Code's sandbox is a concrete version of this. It describes itself plainly: "the Bash sandbox is a boundary that the operating system enforces around the shell commands Claude runs on your machine" — Seatbelt on macOS, `bubblewrap` for filesystem isolation plus `socat` for network relay on Linux and WSL2. By default, writes are confined to the working directory, a per-user temp directory, and directories you've explicitly added, while reads stay broad — including credential files like `~/.ssh` and `~/.aws/credentials`, which is a reminder that a sandbox's defaults are a starting point, not a guarantee. Network access has no direct route out at all; every connection goes through a local proxy checked against an allowlist that starts empty.

The property that matters here isn't the specific mechanism — it's where the check lives. The docs state it directly: "the operating system enforces the sandbox boundary on the running process, so it holds regardless of what the model chose to run, even if an allowed command does more than its name suggests." A monitor can be fooled by a command that looks benign and isn't. A kernel-level filesystem and network boundary doesn't need to recognize the command at all; it just doesn't let an unapproved write or connection happen, full stop.

That strength has an honest limit worth stating alongside it, in the same docs: "sandboxing reduces risk but is not a complete isolation boundary." And it has an operational one too — by default, if the sandbox can't start because a dependency is missing or the platform is unsupported, execution falls back to unsandboxed rather than refusing to run. The `sandbox.failIfUnavailable` setting flips that for deployments that need the boundary to be a hard gate rather than a best effort, which is the right default for anything you don't want running unguarded by accident.

## Key takeaways

A per-action monitor and a circuit breaker are answering different questions, and neither one substitutes for the other. The monitor asks whether this specific action looks wrong; the circuit breaker asks whether too much has happened; the sandbox asks what any action — flagged or not — is physically capable of doing. None of them requires an inference call to decide, and none of the three catches everything the other two would. A loop of individually-approved actions sails past a per-action judge and gets stopped by a turn or token ceiling. An action that *is* individually wrong but still gets approved — by a judge that's wrong, or by no judge at all — gets contained by a sandbox regardless. Cheap oversight isn't one clever detector; it's layering bounds that fail differently from each other, so the gap in one is covered by a different kind of check in the next.

## Further reading

- [OpenAI Agents SDK — Running agents](https://openai.github.io/openai-agents-python/ref/run/) — `max_turns`, turn definition, `MaxTurnsExceeded`
- [OpenAI Agents SDK — Exceptions](https://openai.github.io/openai-agents-python/ref/exceptions/) — exception hierarchy
- [OpenAI Agents SDK — Guardrails](https://openai.github.io/openai-agents-python/guardrails/) — tripwire mechanism, input/output guardrail execution order
- [Claude Code — Sandboxing](https://code.claude.com/docs/en/sandboxing) — OS-enforced filesystem and network boundaries, fail-open default, `sandbox.failIfUnavailable`
