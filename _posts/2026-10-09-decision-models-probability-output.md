---
title: "Decision Models: The Quiet New Category That Three Labs Launched Simultaneously"
description: "What decision models are, how Clef, Strands Decider, pplx-decider, and Jev compare, and when to reach for one instead of a generator."
tags:
    - LLM
    - AI Agents
    - Developer Tools
categories:
    - ai-engineering
header:
    overlay_image: /assets/images/decision-models-probability-output/banner.webp
    overlay_filter: 0.5
    teaser: /assets/images/decision-models-probability-output/teaser.webp
toc: true
toc_sticky: true
---

Your content moderator calls GPT-4o to decide whether to remove a post. It thinks for two seconds, writes four sentences explaining its reasoning, and returns "yes, remove it." You don't read the sentences. Your code throws them away and parses the first word. That call costs twenty times what it needed to, and the two-second pause is now the dominant latency in your request path.

On October 1, 2026, Cloudflare, AWS Strands Labs, and Perplexity each shipped a model designed to stop you from doing exactly this. TypeSafe beat them by more than two weeks with Jev. Nobody coordinated — all four called their products "decision models" independently — and the convergence on the same phrase, the same week, tells you the category has arrived.

## What a decision model is — and is not

A generator takes a prompt and produces a token sequence. A decision model takes structured input and returns a probability distribution. That is the whole difference, and it is a large one.

Every model in this wave shares the same API shape:

- **`state`** — a blob of context. A customer email, a code diff, a structured JSON object, or all three. This is what the model reasons over.
- **`questions`** — a typed map. Each question carries a type, instructions, and any option labels the type needs. All questions are submitted in one call and answered together.

Three question types appear in every implementation:

- **`noul`** — a yes/no question returning the probability of "yes." `P(urgent) = 0.94` is directly consumable by a routing rule; a prose sentence containing "yes" is not.
- **`choice`** — selects one option from a labelled set, returning the chosen option alongside per-option probabilities and a confidence value. There is no string to parse.
- **`score`** — rates position on an ordered rubric, returning a probability-weighted scalar. A sentiment score of 2.3 (out of 10) is arithmetically comparable across requests.

The output is typed data, not prose. That is what makes it directly consumable by application code — and what makes it categorically cheaper to produce.

## Three labs, one morning

**Cloudflare Clef** launched on Workers AI with two variants: standard Clef at 209 ms median and 238 ms p95, and Clef-flash at 38.8 ms median and 122 ms p95. Both are Apache 2.0, hosted, and cost $0.24 per million input tokens. The context window is 65,536 tokens; Clef also accepts up to four embedded images alongside the state. Clef-flash is the fastest hosted option at conversational-request latency — 38.8 ms fits inside a UI interaction budget that no 27B model can touch.

**AWS Strands Decider 2B** went the opposite direction: fully open-source (Apache 2.0), self-hosted, and free. The architecture is public: a Qwen3.5-2B-Base decoder torso with the language-modelling head removed and replaced by a custom pointer head of roughly one million parameters, adapted with a rank-16 LoRA. The pointer head returns scores directly instead of generating text. On an RTX 3090, the v19 checkpoint runs at 115 ms median and 299 ms p95. Install it with `pip install strands-decider` and serve it locally.

**Perplexity pplx-decider-v1.1-27b** is the heaviest of the three: a fine-tune of Qwen3.8-27B, released on Hugging Face under Apache 2.0, with a 262,144-token context window. The hosted API costs $0.04 per million input tokens. Across an 11-benchmark panel of 7,210 samples, Perplexity reports 85.71% accuracy — the highest self-reported number in the group. Latency runs from under two seconds on short prompts to roughly 23 seconds near the context limit. That makes it unsuitable for interactive routing but workable for batch classification.

TypeSafe's **Jev** preceded all three by sixteen days. It is proprietary, waitlisted, and priced at $0.042 per million tokens. TypeSafe calls it a "System One" model, trained on synthetic data using Reinforcement Learning for Calibrated Decisions (RLCD); the architecture is unpublished. Against the same 11-panel Perplexity used, Jev scores 84.51% — second overall — but leads on four specific tests, including WinoGrande (90.70% vs. 83.30%) and BBH (94.27% vs. 82.80%). The API accepts up to 64k tokens per input (32k for state plus the longest question). Questions are answered in parallel — no question can condition on another's answer within a single call.

## How the four compare

| | Clef-flash | Strands 2B | pplx-decider 27b | Jev |
|---|---|---|---|---|
| License | Apache 2.0 | Apache 2.0 | Apache 2.0 | Proprietary |
| Hosting | Workers AI | Self-hosted | Hosted + HF | Waitlisted API |
| Price | $0.24/1M tokens | Free | $0.04/1M tokens | $0.042/1M tokens |
| Base model | Undisclosed | Qwen3.5-2B | Qwen3.8-27B | Undisclosed |
| Median latency | 38.8 ms | ~115 ms | ~2 s | 70–500 ms |
| Accuracy (11-panel) | — | 76.2% (JevBench) | 85.71% | 84.51% |

The six-times price gap between Clef ($0.24/1M) and pplx-decider ($0.04/1M) reflects the cost of serving a 27B model vs. whatever smaller architecture Cloudflare chose. Strands eliminates the cost entirely at the price of owning hardware. Jev at $0.042/1M sits $0.002 per million above pplx-decider — nearly the same cost, with meaningfully lower latency and slightly lower accuracy on the panel that tested both.

The accuracy numbers come from self-reported benchmarks with different methodologies, so treat them as directional, not definitive. Perplexity's 11-panel covers 7,210 samples across diverse tasks; Strands' 76.2% is against the JevBench public set, which is a narrower instrument. No independent third-party comparison across all four exists yet.

## Running the benchmark yourself

The repository includes `script/decision_model_benchmark.py`, which runs four classification tasks across all four providers. In `--dry-run` mode it simulates latencies without API keys, which is useful for validating the integration before committing to any one provider:

```bash
python script/decision_model_benchmark.py --dry-run
```

The four test cases cover a support-ticket urgency and routing decision, a content-moderation policy check, an agent tool-call anomaly (a sandboxed agent issues `read_file('/etc/shadow')` while its stated task is to summarize a README), and a code-review SQL injection flag. Dry-run latencies across those four tests:

| Test | Clef | Perplexity | Jev | Strands |
|---|---|---|---|---|
| support_ticket | 41 ms | 303 ms | 101 ms | 129 ms |
| content_moderation | 48 ms | 311 ms | 86 ms | 106 ms |
| agent_tool_call_routing | 49 ms | 330 ms | 66 ms | 102 ms |
| code_review | 45 ms | 302 ms | 94 ms | 133 ms |
| **avg** | **46 ms** | **311 ms** | **86 ms** | **117 ms** |

Clef-flash wins on raw speed — 2× faster than Jev, 2.5× faster than Strands, 7× faster than pplx-decider. The agent_tool_call_routing case is the one to pay attention to. This is exactly the shape decision models were built for: a guardrail running in the critical path of an agent loop, making one fast binary judgment before each tool call is allowed through. At 49 ms, that check is invisible. At 330 ms, it is the bottleneck.

## When to reach for a generator instead

Decision models do not replace generators for tasks that require synthesis, explanation, or output the user will actually read. The test is simple: if your code would discard the prose to extract a category or a flag, a decision model fits better and costs less.

Practical triggers: you are regex-matching a generator's output for "yes" or "no"; you are prompting a model to return JSON and then parsing it; you are calling `response.split('\n')[0]` to get a label. Each of these is a pattern where a `noul` or `choice` question would eliminate the overhead and remove the parsing failure mode at the same time.

Where generators still win: the answer *is* the prose — a draft email, a code completion, a summary a human reads. The output format is the right criterion, not the task domain.

## Further reading

- Cloudflare Clef changelog — https://developers.cloudflare.com/changelog/post/2026-10-01-clef-workers-ai/
- Cloudflare Workers AI model reference — https://developers.cloudflare.com/workers-ai/models/clef/
- Strands Decider README (GitHub) — https://raw.githubusercontent.com/strands-labs/strands-decider/main/README.md
- Perplexity pplx-decider accuracy panel — https://aiweekly.co/alerts/perplexity-open-sources-27b-decider-edges-jev-on-11-test-panel
- pplx-decider on OpenRouter — https://openrouter.ai/perplexity/pplx-decider-v1.1-27b
