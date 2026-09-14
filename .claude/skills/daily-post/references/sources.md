# Research sources

Used in Stage 2, and in Stage 1 when the topic queue is dry. Prefer primary sources:
specifications, release notes, source code, benchmarks, and papers over secondary
commentary. A blog post summarising a release is not a source — the release notes are.

## Per beat

| Category | Where to look |
| --- | --- |
| `distributed-systems` | Jepsen analyses, etcd/NATS/Kafka release notes, papers from OSDI/SOSP/NSDI, AWS Builders' Library |
| `ai-engineering` | arXiv cs.CL and cs.LG, model and framework release notes, inference-engine benchmarks, MCP and agent-protocol specs |
| `python` | CPython release notes and PEPs, `python/cpython` issues, major library changelogs (asyncio, Pydantic, Polars, uv) |
| `databases` | Postgres release notes and mailing lists, ClickHouse/DuckDB/SQLite changelogs, storage-engine papers |
| `infrastructure` | Kubernetes and CNCF project release notes, OpenTelemetry specs, eBPF and kernel documentation |
| `web-development` | Browser release notes, WHATWG/W3C specs, framework RFCs, HTTP/QUIC RFCs |
| `software-engineering` | Postmortems, language and tooling RFCs, engineering blogs from teams that run the system at scale |

## Discovery when the queue is dry

Scan, in this order, and stop as soon as a candidate survives the duplicate check:

1. Hacker News front page and `news.ycombinator.com/best`, last 48 hours.
2. GitHub releases for projects already covered in the archive — a major version is
   usually worth a post.
3. arXiv listings in cs.DC, cs.SE, cs.CL from the last week.
4. Engineering blogs from teams operating at scale.

A candidate is viable when it is **specific** (a mechanism, not a category), **fresh**
(the reader could not have read this a year ago), and **checkable** (primary sources
exist). Reject anything that would end up as a survey of things that already exist.

## The evidence ledger

Stage 2 produces `research.md` in the scratch directory. Every claim the post will make
appears there as:

```markdown
- **Claim:** JetStream acknowledges a publish before the replica set has fsynced.
  **Source:** https://docs.nats.io/nats-concepts/jetstream/streams
  **Quote:** "..."
```

This file is never published. It exists so the fact gate has something to check
against. **The rule that makes the gate possible: no claim may appear in the post
unless it appears in the ledger.** Write from the ledger, not from recall.

## Why this matters for Gate 2 as well

The duplicate gate (`gates.md`, Gate 2) reads the ledger too, not just the draft: the
same primary source often turns up when researching two different angles on the same
underlying topic, which is itself a signal worth surfacing in that gate's verdict —
a shared source is not proof of duplication, but it is a prompt to check the argument,
not just the wording.
