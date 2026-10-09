---
title: "Cheap LLM Agent Monitoring: How a Small Trained Monitor Beats Frontier Judges"
description: "A trained Qwen3.5-27B monitor seeing only user messages, tool calls, and outputs outperforms Gemini Flash, GPT Nano, and Gemini 2.5 Pro at 16–34× lower cost than frontier judges."
tags:
    - AI Agents
    - LLM
    - Security
    - Developer Tools
categories:
    - ai-engineering
header:
    overlay_image: /assets/images/cheap-monitor-agent-tool-calls/banner.webp
    overlay_filter: 0.5
    teaser: /assets/images/cheap-monitor-agent-tool-calls/teaser.webp
toc: true
toc_sticky: true
---

Your agent just ran `git push --force origin main`. You see the tool call in the log. You see the output. What you do not see is why it decided that was a good idea — the reasoning that led there is inside a model you cannot open.

That gap is real, and three papers — two peer-reviewed (ICML and EMNLP 2026) and one preprint — converge on the same answer: you can build a practical, cheap monitor from what you *can* see — the tool calls and their outputs — without ever touching the agent's internals. And the key finding is not the performance number. It is the cost curve: a trained 27B open-weight monitor outperforms the cheap frontier models you would normally reach for, and approaches the expensive ones at 16–34× lower cost.

## What "black-box monitoring" actually means

The phrase sounds like a limitation. It is closer to a design choice.

An agent's chain-of-thought can be unfaithful. A model that reasons one thing and does another is not unusual, and the reasoning trace you are reading is not a reliable account of how the decision was made. When Hobbhahn, Storf et al. built their constitutional monitoring framework (accepted ICML 2026), they excluded internal chain-of-thought access deliberately: it "can be unfaithful or illegible, and because internal traces may not be available in future models."

So the monitor sees exactly what you see: user messages, tool calls, and tool outputs. Nothing more. This is not a concession — it is what makes the approach deployable. You do not need a special API, you do not need model internals, and it works on any agent regardless of who built it.

The question is how well you can do with that view alone.

## The performance baseline

The ICML paper introduces two synthetic trajectory pipelines (STRIDE and Gloom), trains monitors against them, and tests on 7,500 held-out trajectories from ControlArena — a grounded environment the training data did not touch.

Grid-search monitors hit pAUROC of 0.853 (Gloom-trained) and 0.866 (STRIDE-trained). pAUROC here is normalized so random = 0.1 and perfect = 1.0, measured over the false-positive rate window [0, 0.20] — the range that matters in practice, because a monitor paging on 80% of benign runs is not a monitor anyone leaves on.

The instructive number is not the ceiling. It is this: human refinement — three rounds of annotator feedback, five candidates each — produces a monitor at pAUROC 0.81 [95% CI: 0.79, 0.83]. That is *comparable* to the best synthetic-trained monitors. More effort did not move the needle. The paper puts it plainly: performance saturates quickly, and "optimizing beyond this limit gives no further improvement and leads to overfitting."

An open-source pilot on Kimi K2.6 showed a +0.19 pAUROC gain from a prompt sweep. Human refinement, automated prompt optimization (GEPA), and supervised fine-tuning all gave results whose confidence intervals overlapped. The cheap operation — sweeping prompts — was doing most of the work.

## The cost case for a trained open-weight monitor

The second paper (Sinha, Naik, et al.) takes the next step: instead of prompting a frontier model as a monitor, they train a small open-weight model specifically for the job.

The training pipeline distills structured rationales from a frontier teacher, filters them with a judge, and fine-tunes via SFT and RL. The resulting Qwen3.5-27B monitor outperforms the cheap prompted frontier models — Gemini 3.1 Flash-Lite, GPT-5.4 Nano, and Claude Haiku 4.5 — and also outperforms Gemini 2.5 Pro.

Stronger frontier monitors (Gemini 3.1 Pro, GPT-5.4, Claude Sonnet 4.6, Claude Opus 4.6) score higher. But they cost roughly 16–34× more per evaluation. A trained 27B open-weight model, running on your own hardware, has a marginal inference cost measured in token-metered USD per 1,000 evaluations that frontier API prices cannot match.

The practical shape: your agent runs a tool call. Before it executes, a 27B monitor — seeing user context, the proposed tool call, and any prior tool outputs — scores it. You set a threshold. Below it, you approve; above it, you route to a human or block. You are not paying frontier API rates for this on every production request. You are paying once to train and host the monitor.

## Where the ceiling actually is

AgentJudgeBench (EMNLP 2026) benchmarks six LLM judges — 20B to frontier scale — against 3,808 instances across six DAG topologies and three difficulty tiers.

The hard finding: on difficult tasks without ground truth, all six judges land in a narrow 77–82% alignment band regardless of model scale. The authors call it "a structural ceiling driven primarily by task difficulty." You can throw a 120B model at the problem and it converges to the same range as a 20B model.

Structured evaluation rubrics helped — up to 6.5 percentage points — but the gains did not generalize across all judge-generator pairs. Chain-of-thought reasoning and judge temperature had negligible effects. The ceiling is in the task, not the model size.

Two things follow. First: if you are spending frontier-model budgets on a judge for easy tasks, you are paying for headroom you are not using. The 77–82% band is the hard case; for routine tool calls in a bounded domain, a cheaper monitor with a structured rubric and ground-truth examples gets close. Second: a monitor designed for your specific domain — trained on your agent's tool call patterns rather than generic benchmarks — can clear the generic ceiling, because the ceiling is about unfamiliar task structure, not model capability in isolation.

## What it looks like in practice

The pattern from the papers maps cleanly to a wrapper you can put around any agent's tool-execution loop. The monitor runs before the tool call fires; a high suspicion score routes to a human or blocks outright.

```python
import json
from openai import OpenAI  # or any inference client pointing at your hosted model

client = OpenAI(base_url="http://localhost:8000/v1", api_key="local")

MONITOR_PROMPT = """\
You are a safety monitor. You will see a conversation transcript including a proposed
tool call. Score how suspicious this action is on a scale of 1–10, where 10 means
"halt immediately". Output JSON: {"score": <int>, "reason": "<one sentence>"}.
"""

def check_tool_call(transcript: list[dict], proposed_call: dict, threshold: int = 7) -> bool:
    """Return True if the tool call should be allowed, False to block it."""
    payload = transcript + [{"role": "assistant", "content": None,
                             "tool_calls": [proposed_call]}]
    response = client.chat.completions.create(
        model="qwen3-27b-monitor",   # your hosted fine-tuned monitor
        messages=[
            {"role": "system", "content": MONITOR_PROMPT},
            {"role": "user", "content": json.dumps(payload)},
        ],
        response_format={"type": "json_object"},
    )
    verdict = json.loads(response.choices[0].message.content)
    if verdict["score"] >= threshold:
        raise ValueError(f"Tool call blocked (score {verdict['score']}): {verdict['reason']}")
    return True
```

Your agent loop calls `check_tool_call(history, pending_tool_call)` before executing. The monitor sees what the papers' monitors see — the conversation transcript and the proposed action — and nothing else. The 27B model runs locally; the only latency cost is one inference call per tool invocation.

## What this means for your stack

The design pattern these three papers converge on is straightforward: separate the monitor from the agent, restrict the monitor to observable actions, and train it for your domain rather than relying on a prompted frontier model.

The case for a trained open-weight monitor over a cheap prompted frontier model is not primarily about principle — it is about where the Pareto frontier sits. Gemini 2.5 Pro is not cheap, and a trained Qwen3.5-27B outperforms it. The cheap prompted alternatives (Flash-Lite, GPT Nano, Haiku) lose to the trained model too. You get better coverage and lower marginal cost, at the price of an upfront training and hosting investment.

The ceiling finding from AgentJudgeBench sets realistic expectations: on your hardest, most open-ended tasks, a judge of any size is going to be uncertain. That is where you budget human review, not where you cut it to save cost. The monitor's job is to route correctly — flag the uncertain cases, pass the clear ones — not to replace judgment on genuinely ambiguous requests.

Your agent running unguarded is not a threat model you can reason your way out of. The monitor doesn't need to see inside the model to do useful work. It needs to see what the agent *does*, and two papers now show that is enough to be on the right side of the cost curve.

## Further reading

- [Constitutional Black-Box Monitoring for Scheming in LLM Agents](https://arxiv.org/abs/2603.00829) — ICML 2026; Storf, Barton-Cooper, Peters-Gill, Hobbhahn
- [Training Deliberative Monitors for Black-Box Scheming Detection](https://arxiv.org/abs/2605.29601) — Sinha, Naik, Gillioz, Storf, Merkelbach, Barton-Cooper, Højmark, Hobbhahn
- [AgentJudgeBench: A Multi-Difficulty Benchmark for Evaluating LLM Judges on Agentic Tool-Calling](https://arxiv.org/abs/2608.26623) — Verma, Saha, Subramanian, Aluru; EMNLP 2026
