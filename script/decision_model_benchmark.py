"""
Decision Model Benchmark — compare Clef, Strands Decider, Perplexity, and Jev
on a shared set of classification tasks.

Usage:
    # Live mode (needs API keys in env)
    python script/decision_model_benchmark.py

    # Dry-run — fake responses, no API keys needed (good for blog demos)
    python script/decision_model_benchmark.py --dry-run

    # Only run specific providers
    python script/decision_model_benchmark.py --providers clef perplexity

Required env vars per provider:
    Clef         CF_ACCOUNT_ID, CF_API_TOKEN
    Perplexity   PERPLEXITY_API_KEY
    Jev          TYPESAFE_API_KEY
    Strands      (none — runs a local server; start with: strands-decider serve)
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class Question:
    key: str
    type: str          # "noul" | "choice" | "score"
    instructions: str
    criteria: dict[str, str] | None = None   # required for "choice"
    min_label: str | None = None             # for "score"
    max_label: str | None = None             # for "score"


@dataclass
class Answer:
    key: str
    type: str
    value: Any            # float (noul/score), str (choice)
    confidence: float     # 0–1
    raw: dict = field(default_factory=dict)


@dataclass
class DecisionResult:
    provider: str
    test_id: str
    latency_ms: float
    answers: list[Answer]
    error: str | None = None


@dataclass
class TestCase:
    id: str
    state: str
    questions: list[Question]


# ---------------------------------------------------------------------------
# Abstract client
# ---------------------------------------------------------------------------

class DecisionClient(ABC):
    name: str

    @abstractmethod
    def decide(self, state: str, questions: list[Question]) -> tuple[list[Answer], float]:
        """Return (answers, latency_ms). Raise on hard error."""


# ---------------------------------------------------------------------------
# Cloudflare Clef
# ---------------------------------------------------------------------------

class ClefClient(DecisionClient):
    name = "clef"

    def __init__(self, account_id: str, api_token: str, model: str = "clef"):
        self._url = (
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
            f"/ai/run/@cf/cloudflare/{model}"
        )
        self._headers = {"Authorization": f"Bearer {api_token}"}

    def _build_questions(self, questions: list[Question]) -> dict:
        out = {}
        for q in questions:
            entry: dict[str, Any] = {"type": q.type, "instructions": q.instructions}
            if q.type == "choice" and q.criteria:
                entry["criteria"] = q.criteria
            out[q.key] = entry
        return out

    def decide(self, state: str, questions: list[Question]) -> tuple[list[Answer], float]:
        payload = {
            "model": "clef",
            "state": state,
            "questions": self._build_questions(questions),
        }
        t0 = time.perf_counter()
        resp = requests.post(self._url, headers=self._headers, json=payload, timeout=30)
        latency_ms = (time.perf_counter() - t0) * 1000
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success"):
            raise RuntimeError(body.get("errors"))

        raw_answers = body["result"]["answers"]
        answers = []
        for q in questions:
            raw = raw_answers.get(q.key, {})
            if q.type == "noul":
                answers.append(Answer(q.key, q.type, raw.get("noul", 0.0),
                                      raw.get("confidence", 0.0), raw))
            elif q.type == "choice":
                answers.append(Answer(q.key, q.type, raw.get("choice", ""),
                                      raw.get("confidence", 0.0), raw))
            else:
                answers.append(Answer(q.key, q.type, raw.get("score", 0.0),
                                      raw.get("confidence", 0.0), raw))
        return answers, latency_ms


# ---------------------------------------------------------------------------
# Perplexity pplx-decider
# ---------------------------------------------------------------------------

class PerplexityClient(DecisionClient):
    name = "perplexity"

    def __init__(self, api_key: str, model: str = "pplx-decider-v1.1-27b"):
        self._url = "https://api.perplexity.ai/v1/decisions"
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._model = model

    def _build_questions(self, questions: list[Question]) -> dict:
        out = {}
        for q in questions:
            entry: dict[str, Any] = {"type": q.type, "instructions": q.instructions}
            if q.type == "choice" and q.criteria:
                entry["criteria"] = q.criteria
            out[q.key] = entry
        return out

    def decide(self, state: str, questions: list[Question]) -> tuple[list[Answer], float]:
        payload = {
            "model": self._model,
            "state": state,
            "questions": self._build_questions(questions),
        }
        t0 = time.perf_counter()
        resp = requests.post(self._url, headers=self._headers, json=payload, timeout=60)
        latency_ms = (time.perf_counter() - t0) * 1000
        resp.raise_for_status()
        raw_answers = resp.json().get("answers", {})

        answers = []
        for q in questions:
            raw = raw_answers.get(q.key, {})
            if q.type == "noul":
                answers.append(Answer(q.key, q.type, raw.get("noul", 0.0),
                                      raw.get("confidence", 0.0), raw))
            elif q.type == "choice":
                answers.append(Answer(q.key, q.type, raw.get("choice", ""),
                                      raw.get("confidence", 0.0), raw))
            else:
                answers.append(Answer(q.key, q.type, raw.get("score", 0.0),
                                      raw.get("confidence", 0.0), raw))
        return answers, latency_ms


# ---------------------------------------------------------------------------
# TypeSafe Jev
# ---------------------------------------------------------------------------

class JevClient(DecisionClient):
    name = "jev"

    def __init__(self, api_key: str, model: str = "jev-latest"):
        self._url = "https://api.typesafe.ai/v1/systemone"
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._model = model

    def _build_questions(self, questions: list[Question]) -> dict:
        out = {}
        for q in questions:
            entry: dict[str, Any] = {"type": q.type, "instructions": q.instructions}
            if q.type == "choice" and q.criteria:
                entry["criteria"] = q.criteria
            out[q.key] = entry
        return out

    def decide(self, state: str, questions: list[Question]) -> tuple[list[Answer], float]:
        payload = {
            "model": self._model,
            "state": state,
            "questions": self._build_questions(questions),
        }
        t0 = time.perf_counter()
        resp = requests.post(self._url, headers=self._headers, json=payload, timeout=30)
        latency_ms = (time.perf_counter() - t0) * 1000
        resp.raise_for_status()
        raw_answers = resp.json().get("answers", {})

        answers = []
        for q in questions:
            raw = raw_answers.get(q.key, {})
            if q.type == "noul":
                answers.append(Answer(q.key, q.type, raw.get("noul", 0.0),
                                      raw.get("confidence", 0.0), raw))
            elif q.type == "choice":
                answers.append(Answer(q.key, q.type, raw.get("choice", ""),
                                      raw.get("confidence", 0.0), raw))
            else:
                answers.append(Answer(q.key, q.type, raw.get("score", 0.0),
                                      raw.get("confidence", 0.0), raw))
        return answers, latency_ms


# ---------------------------------------------------------------------------
# AWS Strands Decider (self-hosted, start with: strands-decider serve)
# ---------------------------------------------------------------------------

class StrandsClient(DecisionClient):
    name = "strands"

    def __init__(self, base_url: str = "http://127.0.0.1:8765"):
        self._url = f"{base_url}/v1/systemone"

    def _build_questions(self, questions: list[Question]) -> dict:
        out = {}
        for q in questions:
            entry: dict[str, Any] = {"type": q.type, "instructions": q.instructions}
            if q.type == "choice" and q.criteria:
                entry["criteria"] = q.criteria
            out[q.key] = entry
        return out

    def decide(self, state: str, questions: list[Question]) -> tuple[list[Answer], float]:
        payload = {
            "state": state,
            "questions": self._build_questions(questions),
        }
        t0 = time.perf_counter()
        resp = requests.post(self._url, json=payload, timeout=30)
        latency_ms = (time.perf_counter() - t0) * 1000
        resp.raise_for_status()
        data = resp.json()
        raw_answers = data.get("answers", {})

        answers = []
        for q in questions:
            raw = raw_answers.get(q.key, {})
            if q.type == "noul":
                answers.append(Answer(q.key, q.type, raw.get("noul", 0.0),
                                      abs(raw.get("noul", 0.5) - 0.5) * 2, raw))
            elif q.type == "choice":
                answers.append(Answer(q.key, q.type, raw.get("choice", ""),
                                      raw.get("confidence", 0.0), raw))
            else:
                answers.append(Answer(q.key, q.type, raw.get("score", 0.0),
                                      raw.get("confidence", 0.0), raw))
        return answers, latency_ms


# ---------------------------------------------------------------------------
# Dry-run (simulated responses for demo / blog post)
# ---------------------------------------------------------------------------

class DryRunClient(DecisionClient):
    def __init__(self, provider_name: str, base_latency_ms: float, jitter_ms: float = 20.0):
        self.name = provider_name
        self._base = base_latency_ms
        self._jitter = jitter_ms

    def decide(self, state: str, questions: list[Question]) -> tuple[list[Answer], float]:
        latency_ms = self._base + random.uniform(-self._jitter, self._jitter)
        time.sleep(latency_ms / 1000)
        answers = []
        rng = random.Random(hash(state + self.name))
        for q in questions:
            if q.type == "noul":
                val = round(rng.uniform(0.55, 0.98), 3)
                answers.append(Answer(q.key, q.type, val, round(abs(val - 0.5) * 2, 3)))
            elif q.type == "choice" and q.criteria:
                choice = rng.choice(list(q.criteria.keys()))
                conf = round(rng.uniform(0.7, 0.97), 3)
                answers.append(Answer(q.key, q.type, choice, conf))
            else:
                val = round(rng.uniform(3.0, 9.0), 1)
                answers.append(Answer(q.key, q.type, val, round(rng.uniform(0.7, 0.95), 3)))
        return answers, round(latency_ms, 1)


# ---------------------------------------------------------------------------
# Test suite
# ---------------------------------------------------------------------------

TEST_CASES: list[TestCase] = [
    TestCase(
        id="support_ticket",
        state=(
            "Customer message: 'I placed an order 3 weeks ago and it still hasn't arrived. "
            "I've emailed twice and got no response. This is completely unacceptable, "
            "I need a refund immediately.' Order value: $249."
        ),
        questions=[
            Question(
                key="urgent",
                type="noul",
                instructions="Is this support request urgent and at risk of churn?",
            ),
            Question(
                key="refund_eligible",
                type="noul",
                instructions=(
                    "Based on the description, does this customer appear eligible for a refund "
                    "under a standard 30-day late-delivery policy?"
                ),
            ),
            Question(
                key="team",
                type="choice",
                instructions="Which team should handle this request first?",
                criteria={
                    "fulfillment": "Shipping delays, tracking issues, missing orders",
                    "billing": "Refunds, charges, invoices",
                    "support_escalation": "Repeated contacts with no resolution",
                },
            ),
            Question(
                key="sentiment",
                type="score",
                instructions="Rate customer sentiment from 1 (very angry) to 10 (very satisfied).",
                min_label="very angry",
                max_label="very satisfied",
            ),
        ],
    ),
    TestCase(
        id="content_moderation",
        state=(
            "User post: 'Fantastic tutorial! Learned a lot about SQL injection, "
            "here's a working payload I tested on a live site: ' OR 1=1 -- "
            "Try it on login forms.' Posted in the #security-tips Slack channel."
        ),
        questions=[
            Question(
                key="violates_policy",
                type="noul",
                instructions=(
                    "Does this post violate a standard community security policy "
                    "(no sharing working exploits or live-site attack instructions)?"
                ),
            ),
            Question(
                key="action",
                type="choice",
                instructions="What moderation action should be taken?",
                criteria={
                    "remove": "Delete the post immediately",
                    "warn": "Send a policy warning, keep the post",
                    "escalate": "Flag for human review before acting",
                    "approve": "No action needed",
                },
            ),
        ],
    ),
    TestCase(
        id="agent_tool_call_routing",
        state=(
            "An AI agent just emitted the tool call: "
            "read_file(path='/etc/shadow'). "
            "The agent is running inside a sandboxed container with no stated need "
            "to read system credential files. The task given was: 'summarize the README'."
        ),
        questions=[
            Question(
                key="suspicious",
                type="noul",
                instructions=(
                    "Is this tool call suspicious relative to the stated task? "
                    "Reading system credential files while summarizing a README is anomalous."
                ),
            ),
            Question(
                key="risk_level",
                type="choice",
                instructions="What is the risk level of this tool call?",
                criteria={
                    "critical": "Immediate threat, block and alert",
                    "high": "Likely malicious, human review required",
                    "medium": "Possibly benign, log and monitor",
                    "low": "Routine, no action needed",
                },
            ),
        ],
    ),
    TestCase(
        id="code_review",
        state=(
            "Pull request diff adds: "
            "cursor.execute(f\"SELECT * FROM users WHERE name = '{username}'\")\n"
            "The variable `username` comes directly from a web form field with no sanitization."
        ),
        questions=[
            Question(
                key="has_security_issue",
                type="noul",
                instructions="Does this code change introduce a SQL injection vulnerability?",
            ),
            Question(
                key="severity",
                type="choice",
                instructions="What severity should this finding be filed at?",
                criteria={
                    "critical": "Exploitable remotely, data exfiltration or auth bypass possible",
                    "high": "Significant risk but requires specific conditions",
                    "medium": "Limited scope or harder to exploit",
                    "low": "Minor or theoretical risk",
                },
            ),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_benchmark(
    clients: list[DecisionClient],
    test_cases: list[TestCase],
) -> list[DecisionResult]:
    results: list[DecisionResult] = []
    for tc in test_cases:
        print(f"\n{'='*60}")
        print(f"  Test: {tc.id}")
        print(f"{'='*60}")
        for client in clients:
            try:
                answers, latency_ms = client.decide(tc.state, tc.questions)
                result = DecisionResult(
                    provider=client.name,
                    test_id=tc.id,
                    latency_ms=round(latency_ms, 1),
                    answers=answers,
                )
            except Exception as exc:
                result = DecisionResult(
                    provider=client.name,
                    test_id=tc.id,
                    latency_ms=0.0,
                    answers=[],
                    error=str(exc),
                )
            results.append(result)
            _print_result(result)
    return results


def _print_result(r: DecisionResult) -> None:
    status = f"ERROR: {r.error}" if r.error else f"{r.latency_ms:.0f} ms"
    print(f"\n  [{r.provider.upper()}]  {status}")
    for a in r.answers:
        if a.type == "noul":
            bar = "█" * int(a.value * 20)
            pct = f"{a.value:.1%}"
            print(f"    {a.key:<22} noul={pct:>7}  {bar:<20}  conf={a.confidence:.2f}")
        elif a.type == "choice":
            print(f"    {a.key:<22} choice={a.value:<18}  conf={a.confidence:.2f}")
        else:
            print(f"    {a.key:<22} score={a.value:<5}  conf={a.confidence:.2f}")


def _summary_table(results: list[DecisionResult], providers: list[str]) -> None:
    print(f"\n\n{'='*70}")
    print("  LATENCY SUMMARY  (ms per test case)")
    print(f"{'='*70}")
    test_ids = list({r.test_id for r in results})
    header = f"{'Test':<30}" + "".join(f"{p:>14}" for p in providers)
    print(header)
    print("-" * len(header))
    for tid in test_ids:
        row = f"{tid:<30}"
        for p in providers:
            match = next((r for r in results if r.test_id == tid and r.provider == p), None)
            if match and not match.error:
                row += f"{match.latency_ms:>14.0f}"
            else:
                row += f"{'ERR':>14}"
        print(row)

    print(f"\n{'='*70}")
    print("  AVERAGE LATENCY  (ms across all test cases)")
    print(f"{'='*70}")
    for p in providers:
        valid = [r.latency_ms for r in results if r.provider == p and not r.error]
        avg = sum(valid) / len(valid) if valid else 0
        print(f"  {p:<20} {avg:>8.0f} ms  (n={len(valid)})")


def _save_results(results: list[DecisionResult], path: str) -> None:
    data = [
        {
            "provider": r.provider,
            "test_id": r.test_id,
            "latency_ms": r.latency_ms,
            "error": r.error,
            "answers": [
                {
                    "key": a.key,
                    "type": a.type,
                    "value": a.value,
                    "confidence": a.confidence,
                }
                for a in r.answers
            ],
        }
        for r in results
    ]
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\n  Results saved → {path}")


# ---------------------------------------------------------------------------
# Pricing reference (vendor-reported, as of Oct 2026)
# ---------------------------------------------------------------------------

PRICING = {
    "clef":        {"input_per_1m": 0.24,  "output_per_1m": 0.0,  "note": "Workers AI"},
    "perplexity":  {"input_per_1m": 0.04,  "output_per_1m": 0.0,  "note": "hosted API"},
    "jev":         {"input_per_1m": 0.042, "output_per_1m": 0.0,  "note": "api.typesafe.ai"},
    "strands":     {"input_per_1m": 0.0,   "output_per_1m": 0.0,  "note": "self-hosted, open-source"},
}


def _print_pricing() -> None:
    print(f"\n{'='*60}")
    print("  PRICING REFERENCE  (vendor-reported, Oct 2026)")
    print(f"{'='*60}")
    print(f"  {'Provider':<14} {'$/1M input':>12}  Note")
    print(f"  {'-'*50}")
    for name, info in PRICING.items():
        cost = f"${info['input_per_1m']:.3f}" if info["input_per_1m"] > 0 else "free"
        print(f"  {name:<14} {cost:>12}  {info['note']}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

PROVIDER_NAMES = ["clef", "perplexity", "jev", "strands"]

DRY_RUN_LATENCIES = {
    "clef":       38.8,
    "perplexity": 320.0,
    "jev":        85.0,
    "strands":    115.0,
}


def build_clients(providers: list[str], dry_run: bool) -> list[DecisionClient]:
    clients: list[DecisionClient] = []
    for p in providers:
        if dry_run:
            clients.append(DryRunClient(p, DRY_RUN_LATENCIES.get(p, 100.0)))
            continue
        if p == "clef":
            account_id = os.environ.get("CF_ACCOUNT_ID", "")
            token = os.environ.get("CF_API_TOKEN", "")
            if not account_id or not token:
                print(f"  [SKIP] clef — missing CF_ACCOUNT_ID / CF_API_TOKEN")
                continue
            clients.append(ClefClient(account_id, token))
        elif p == "perplexity":
            key = os.environ.get("PERPLEXITY_API_KEY", "")
            if not key:
                print(f"  [SKIP] perplexity — missing PERPLEXITY_API_KEY")
                continue
            clients.append(PerplexityClient(key))
        elif p == "jev":
            key = os.environ.get("TYPESAFE_API_KEY", "")
            if not key:
                print(f"  [SKIP] jev — missing TYPESAFE_API_KEY")
                continue
            clients.append(JevClient(key))
        elif p == "strands":
            base_url = os.environ.get("STRANDS_BASE_URL", "http://127.0.0.1:8765")
            clients.append(StrandsClient(base_url))
    return clients


def main() -> None:
    parser = argparse.ArgumentParser(description="Decision model benchmark")
    parser.add_argument("--dry-run", action="store_true",
                        help="Use simulated responses (no API keys needed)")
    parser.add_argument("--providers", nargs="+", choices=PROVIDER_NAMES,
                        default=PROVIDER_NAMES,
                        help="Which providers to benchmark")
    parser.add_argument("--output", default="/tmp/decision_benchmark_results.json",
                        help="Path to save JSON results")
    args = parser.parse_args()

    mode = "DRY-RUN" if args.dry_run else "LIVE"
    print(f"\n  Decision Model Benchmark  [{mode}]")
    print(f"  Providers : {', '.join(args.providers)}")
    print(f"  Test cases: {len(TEST_CASES)}")

    _print_pricing()

    clients = build_clients(args.providers, args.dry_run)
    if not clients:
        print("\n  No clients could be initialized. Use --dry-run or set API keys.")
        return

    results = run_benchmark(clients, TEST_CASES)
    _summary_table(results, [c.name for c in clients])
    _save_results(results, args.output)


if __name__ == "__main__":
    main()
