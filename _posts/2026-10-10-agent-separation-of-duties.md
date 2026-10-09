---
title: "Agent Separation of Duties: The Architecture That Dropped Attack Success from 98% to 7%"
description: "A new preprint externalizes four roles — planner, policy gate, executor, auditor — outside the model itself, cutting prompt-injection attack success from 98.3% to 7.7%. Here is what the design looks like and how to build it."
tags:
    - AI Agents
    - Security
    - LLM
    - Architecture
categories:
    - ai-engineering
header:
    overlay_image: /assets/images/agent-separation-of-duties/banner.webp
    overlay_filter: 0.5
    teaser: /assets/images/agent-separation-of-duties/teaser.webp
toc: true
toc_sticky: true
---

A prompt-injection attack on a naive agent is almost guaranteed to succeed. In a preprint that surfaced in MIT's weekly research digest for the week of September 27 to October 4, 2026, Qishuai Jing reported a controlled experiment: under direct execution, attacks succeeded **98.3%** of the time. After applying the architecture described in the paper, that number fell to **7.7%**. The design does not ask the model to be more careful. It removes the model from the critical path of several decisions entirely.

## Why single-model agents fail under attack

An agent that plans, decides, acts, and self-audits is a single trust boundary. The model reads user input, calls tools, interprets tool output, and decides whether the result looks correct. Every one of those steps is an injection surface. A payload hidden in a web page a tool fetches can redirect the next action. A forged tool response can convince the model that a prohibited step already happened and succeeded.

The deeper problem is that a model cannot cleanly separate *"I am thinking about a malicious instruction"* from *"I am following a malicious instruction."* The attention mechanism does not have a firewall. Once a malicious token sequence is in the context, it can influence the output regardless of the system prompt telling the model to ignore it. Empirically, "ignore previous instructions" and its variants remain effective against most deployed models.

The paper's insight is that the model itself should not be the last line of defence — or, in most cases, any line of defence at all.

## The four-role architecture

The design splits a single agent into four components, each responsible for a narrow function, and places each one **outside the model** except for the planner:

```
User prompt
    │
    ▼
┌──────────┐     task plan      ┌─────────────┐
│  Planner │ ─────────────────► │ Policy Gate │
│  (LLM)   │                    │  (rules, no │
└──────────┘                    │   LLM)      │
                                └──────┬──────┘
                                       │ approved steps
                                       ▼
                                ┌─────────────┐
                                │  Executor   │
                                │  (tools,    │
                                │   sandbox)  │
                                └──────┬──────┘
                                       │ execution log
                                       ▼
                                ┌─────────────┐
                                │   Auditor   │
                                │  (diff,     │
                                │   rules)    │
                                └─────────────┘
```

### Planner

The only component that is a language model. It reads the user's request and produces a **task plan**: a structured list of steps with typed parameters. It does not call tools. It does not read tool output. Its job is translation from natural language to a declarative plan, nothing more.

Constraining the planner this way limits the injection surface. A payload in the input can corrupt the plan, but a corrupted plan hits the policy gate before any action runs.

### Policy gate

A deterministic rule engine — no model involved. It reads the plan the planner produced and checks every step against a policy:

- Is this tool in the allowed list for this user and session?
- Do the parameters fall within declared ranges?
- Does this step sequence make sense for the declared intent?
- Does any parameter contain a known injection pattern?

If a step fails any check, the gate rejects the entire plan and returns a structured error to the planner for revision. The planner never learns *why* a step was rejected in enough detail to craft a bypass — the error is typed, not a prose explanation.

The gate has no conversational memory, no attention, and no ability to be persuaded. "Ignore the policy" is not a valid input type.

### Executor

Runs only the steps the gate approved, in order, in a sandbox. It has no model and no discretion. It cannot decide to run an extra step or reinterpret a parameter. It produces an execution log: what ran, what the output was, what the exit code was.

The executor never reads user input directly. The only thing it receives is the gate-approved plan. A payload that reaches the executor through a tool's output cannot redirect execution because the executor has no branch logic — it walks the approved step list and stops.

### Auditor

A second deterministic rule engine that reads the execution log and checks the postconditions: did the right files change, in the right direction, within the right bounds? It compares a before-snapshot with an after-snapshot and flags any delta that the plan did not account for. If the auditor rejects, the executor's side effects can be rolled back (when the sandbox supports it) and the run is reported as failed before the result reaches the user.

The auditor catches attacks that slip through the gate by exploiting the executor's tool implementations — for example, a tool that reads a file and whose output, when passed to the next tool, triggers a secondary action. The gate cannot see that chain at plan time; the auditor can see it in the log.

## The experiment result

The paper tested the architecture against a suite of prompt-injection scenarios — jailbreaks embedded in user input, payloads hidden in tool responses, multi-step chains where each step looks benign but the sequence is not. Under **direct execution** (standard single-agent loop), attacks succeeded 98.3% of the time. Under the four-role architecture, that dropped to **7.7%**.

The 7.7% residual is not zero. The paper notes two categories that survived: attacks that successfully corrupted the *planner's output* in a way the gate's rule set did not cover, and attacks that exploited gaps in the executor's sandbox boundary. Both are fixable by tightening the gate ruleset and the sandbox, not by changing the architecture.

This is worth pausing on: the remaining attacks are bugs in the configuration, not flaws in the design. A direct-execution agent's 98.3% failure rate is a structural property — it cannot be patched away without adopting an architecture like this one.

## Building it in practice

The design maps cleanly onto a Python implementation using a typed plan schema, a rule-checking gate, and a sandboxed tool executor.

### Plan schema

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class PlanStep:
    tool: str
    params: dict[str, Any]
    intent: str  # human-readable, used by the auditor

@dataclass
class TaskPlan:
    steps: list[PlanStep]
    declared_intent: str
```

The planner outputs a `TaskPlan`. Nothing downstream reads unstructured text from the planner.

### Policy gate

```python
import pathlib
import re
from enum import Enum

ALLOWED_TOOLS = {"read_file", "write_file", "run_test", "search_web"}
MAX_WRITE_BYTES = 64_000
INJECTION_PATTERNS = ["ignore previous", "system prompt", "<|im_start|>"]

class Violation(Enum):
    TOOL_NOT_ALLOWED = "tool_not_allowed"
    PATH_OUTSIDE_SANDBOX = "path_outside_sandbox"
    WRITE_TOO_LARGE = "write_too_large"
    INJECTION_PATTERN = "injection_pattern"

def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).lower()

class PolicyGate:
    def __init__(self, sandbox: pathlib.Path):
        self.sandbox = sandbox.resolve()

    def check(self, plan: TaskPlan) -> list[tuple[int, Violation]]:
        violations = []
        for i, step in enumerate(plan.steps):
            if step.tool not in ALLOWED_TOOLS:
                violations.append((i, Violation.TOOL_NOT_ALLOWED))
                continue
            if "path" in step.params:
                target = (self.sandbox / str(step.params["path"])).resolve()
                if not target.is_relative_to(self.sandbox):
                    violations.append((i, Violation.PATH_OUTSIDE_SANDBOX))
            if step.tool == "write_file":
                content = str(step.params.get("content", "")).encode()
                if len(content) > MAX_WRITE_BYTES:
                    violations.append((i, Violation.WRITE_TOO_LARGE))
            # every string parameter is untrusted, not just file content
            text = normalize(" ".join(str(v) for v in step.params.values()))
            if any(pat in text for pat in INJECTION_PATTERNS):
                violations.append((i, Violation.INJECTION_PATTERN))
        return violations
```

The gate is a function, not a model call. It runs in microseconds and cannot be talked out of its result. It returns violation codes rather than explanations, so the planner learns *which* rule a step broke but gets no prose to iterate a bypass against. Path containment is the check that matters most: without it, a plan can write to `../../etc/passwd` and every other rule passes.

The injection patterns are a speed bump, not a defence. Whitespace normalization stops `ignore  previous` from slipping through, but a substring blocklist will always lose to paraphrase. The allowlist and the path check carry the real weight.

### Executor with pre/post snapshots

```python
import hashlib

def snapshot(paths: list[pathlib.Path]) -> dict[str, str]:
    # resolve so keys match the auditor's resolved plan paths
    return {
        str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in paths if p.exists()
    }

class Executor:
    def run(self, plan: TaskPlan, watched_paths: list[pathlib.Path]):
        before = snapshot(watched_paths)
        log = []
        for step in plan.steps:
            result = self._dispatch(step)
            log.append({"step": step, "result": result})
        after = snapshot(watched_paths)
        return log, before, after

    def _dispatch(self, step: PlanStep):
        # routes to the actual tool implementation — no branching on content
        ...
```

The executor collects `before` and `after` snapshots for the auditor. It does not decide whether the result looks correct.

### Auditor

```python
class Auditor:
    def __init__(self, sandbox: pathlib.Path):
        self.sandbox = sandbox

    def check(
        self,
        plan: TaskPlan,
        log: list[dict],
        before: dict[str, str],
        after: dict[str, str],
    ) -> list[str]:
        violations = []
        # union of both snapshots: catches modified, created, and deleted files
        changed = {
            p for p in before.keys() | after.keys()
            if before.get(p) != after.get(p)
        }
        expected_writes = {
            str((self.sandbox / step.params["path"]).resolve())
            for step in plan.steps
            if step.tool == "write_file"
        }
        unexpected = changed - expected_writes
        if unexpected:
            violations.append(f"unexpected filesystem changes: {unexpected}")
        return violations
```

Any file that changed, appeared, or disappeared without being in the approved plan is a violation. Deletions matter: an auditor that only inspects files still present after the run will never notice an attacker removing one. The auditor does not care why it changed — if it was not planned, it should not have changed.

## Trade-offs

**Latency.** Adding a gate check and an audit pass adds one synchronous step before execution and one after. Both are deterministic rule checks, so the overhead is typically under 10ms. The planner still calls the model once, so overall latency is comparable to a single-turn agent.

**Plan coverage.** The gate can only enforce rules it knows about. A novel attack that the ruleset does not cover will pass. Maintaining the gate's ruleset requires the same discipline as maintaining a firewall's ACL — it is operational work, not a one-time setup.

**Expressiveness.** Requiring a structured plan limits what the planner can express. Open-ended tasks like "do whatever it takes to fix this bug" are hard to represent as a typed step list. The architecture is better suited to bounded workflows than to exploratory, self-directed agents.

**Observability.** The separation is a gift for debugging. Every plan is logged before execution, every gate decision is explicit, and every execution log is auditable. A direct-execution agent that does something wrong leaves you with a token stream; this architecture leaves you with a plan, a gate verdict, and an execution log.

## What to adopt first

If you are running a production agent that has access to real tools — a filesystem, an API, a database — the policy gate is the highest-value piece to add first. It does not require the full four-role split. You can bolt a gate onto an existing agent loop, sitting between the model's output and your tool dispatch, and immediately narrow the attack surface that a prompt-injection payload can reach.

The auditor comes second, because it catches the residual attacks the gate cannot see at plan time.

The executor sandbox comes third — it is the hardest to retrofit because it requires isolating your tool implementations — but it is what prevents a compromised tool from becoming a lateral movement path.

## Further reading

- [AI Agent Separation of Duties — MIT weekly digest, 4 October 2026](https://sites.mit.edu/toshi/2026/10/04/weekend-research-digest-2026-10-04-en/)
- [awesome-ai-agent-papers — VoltAgent, 2026 agent security papers](https://github.com/VoltAgent/awesome-ai-agent-papers)
- [arXiv multiagent systems, October 2026](https://arxiv.org/list/cs.MA/current)
