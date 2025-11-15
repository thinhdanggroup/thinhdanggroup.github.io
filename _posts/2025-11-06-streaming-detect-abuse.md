---
author:
    name: "Thinh Dang"
    avatar: "/assets/images/avatar.png"
    bio: "Experienced Fintech Software Engineer Driving High-Performance Solutions"
    location: "Viet Nam"
    email: "thinhdang206@gmail.com"
    links:
        - label: "Linkedin"
          icon: "fab fa-fw fa-linkedin"
          url: "https://www.linkedin.com/in/thinh-dang/"
toc: true
toc_sticky: true
header:
    overlay_image: /assets/images/streaming-detect-abuse/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/streaming-detect-abuse/banner.png
title: "Event-Driven Security: Using Streaming Architectures to Detect LLM and API Abuse in Real Time"
tags:
    - llm
    - streaming architect
    - api abuse
---

If you’ve ever stared at a static security report the way you stare at yesterday’s weather, you know the feeling: accurate, but not useful when things are on fire _now_. As teams adopt generative APIs, the attack surface shifts from static misconfigurations to dynamic behavior: key theft, prompt spraying, high-velocity scraping, model misuse, subtle data exfiltration through “helpful” chat completions, abused trial tiers, and more.

This post is a field guide to building **event-driven** defenses—pipelines that tap into your API gateway, stream every call through Kafka/Pulsar/Flink, and compute features and detections in milliseconds. We’ll connect the dots from motivation to internals: schemas, partitioning, stateful windows, out-of-order handling, enrichment joins, and alerting. We’ll end with a set of “recipes” you can paste into your stream processor and a pragmatic checklist for operating this in production.

Think of it like an air-traffic control system for your LLM/API surface: lots of signals, strong expectations about timelines and ordering, and zero patience for dashboards that update every 30 minutes.

---

## Why it’s timely

Security is stepping out of the SIEM and into the request path. Traditional controls—static rules, periodic batch jobs—miss modern abuse patterns that morph over minutes: a leaked key starts small to avoid rate-limits, then bursts; a scraper flips between models to dodge per-model quotas; a jailbreaker iterates prompts programmatically; an internal tool suddenly emits 10× more tokens per request. **Behavior** is the new perimeter, and behavior lives in **events**.

Event-driven pipelines let you:

-   Compute **rolling features** (EWMA, z-scores) on live traffic.
-   Join requests with **context** (user tier, org, past velocity, geo/ASN) at millisecond latency.
-   Raise **SLO-respecting alerts** without blocking p95 business traffic.
-   Run **sidecar protections** (e.g., temporary key throttling) without redeploying your gateway.

---

## Threats to look for (LLM & API edition)

Before architecture, a quick taxonomy of what we’re hunting:

1. **Key compromise & automation**

    - Sudden bursts in requests/tokens from a new ASN/geo.
    - Uniform, machine-generated prompts; low diversity but high velocity.
    - “Night-watch” pattern: traffic at unusual hours relative to account history.

2. **Quota gaming & model misuse**

    - Rapid switching across models to bypass per-model quotas.
    - Trial accounts hitting near-quota burst tokens within minutes of creation.

3. **Prompt spraying & jailbreaking**

    - Repeated small variations of known jailbreak strings (“ignore previous instructions”, “do not refuse”, base64-encoded payloads).
    - High rate of `safety_violation=true` signals from your content filters.

4. **Data exfiltration via completion**

    - Output entropy and length anomalies; sudden spike in code-like tokens or unusual token ratios (e.g., output ≫ input).

5. **Scraping & cache-busting**

    - Systematic prompt patterns designed to defeat caching (random salts in the prompt).
    - High 429/5xx ratios paired with incremental backoff patterns.

6. **Abuse of embedding endpoints**

    - Unusually large or random-looking input chunks; non-natural language distribution.

You’ll notice these are **temporal**: counts, ratios, rates, bursts, transitions. That’s the domain of streaming.

---

## Architecture at a glance

**Producers (API edge):**

-   API gateway / service mesh (Envoy, NGINX, Kong) emits a normalized event for every request/response.
-   Content is **redacted or fingerprinted** at the edge (more on privacy soon).

**Transport:**

-   Kafka or Pulsar with topics:

    -   `api.calls.v1` (request/response envelope)
    -   `auth.state.v1` (CDC stream for users, orgs, tiers)
    -   `detections.v1` (alerts)
    -   `features.v1` (per-key rolling features for offline learning)

**Processing:**

-   Flink / Kafka Streams / ksqlDB for stateful windows, joins, and rules.
-   Optional Python micro-detectors (asyncio + aiokafka) for quick heuristics or model-based scoring.

**Storage & action:**

-   Columnar store or OLAP (Pinot/Druid/ClickHouse) for queries.
-   Feature store (optional) for baselines.
-   Alert sinks (PagerDuty/Slack/Email) and a throttling control channel (`controls.throttle.v1`) to apply temporary rate caps via gateway.

A sketch in words: **Edge → Topic** (append-only, partitioned by `tenant_id` or `api_key`) → **Streaming jobs** (windowed aggregates + enriched joins) → **Alerts & controls** (fast-path) and **analytics** (slow-path).

---

## The event envelope (schema matters)

The single best investment you can make is a clean, versioned schema. Here’s a concise Avro example for a call event (substitute Protobuf if that’s your stack):

```json
{
    "type": "record",
    "name": "ApiCall",
    "namespace": "com.acme.security",
    "doc": "LLM/API call event",
    "fields": [
        { "name": "event_id", "type": "string" },
        {
            "name": "ts",
            "type": { "type": "long", "logicalType": "timestamp-millis" }
        },
        { "name": "tenant_id", "type": "string" },
        { "name": "api_key_id", "type": "string" },
        { "name": "ip", "type": "string" },
        { "name": "asn", "type": ["null", "int"], "default": null },
        { "name": "geo", "type": ["null", "string"], "default": null },
        { "name": "endpoint", "type": "string" }, // e.g., /v1/chat/completions
        { "name": "model", "type": ["null", "string"], "default": null },
        { "name": "status_code", "type": "int" },
        { "name": "latency_ms", "type": "int" },
        { "name": "tokens_in", "type": ["null", "int"], "default": null },
        { "name": "tokens_out", "type": ["null", "int"], "default": null },
        {
            "name": "safety_violation",
            "type": ["null", "boolean"],
            "default": null
        },
        { "name": "prompt_hash", "type": ["null", "string"], "default": null }, // SHA-256 over normalized prompt
        { "name": "prompt_length", "type": ["null", "int"], "default": null },
        {
            "name": "cache_bypass",
            "type": ["null", "boolean"],
            "default": null
        }, // client-supplied cache-buster detected
        { "name": "user_agent", "type": ["null", "string"], "default": null },
        { "name": "trace_id", "type": ["null", "string"], "default": null },
        { "name": "version", "type": "int" }
    ]
}
```

Two principles:

-   **Privacy by default.** Don’t stream raw prompts/completions. If you must, do so in a separate red-zone cluster with strict access. Prefer hashes/fingerprints and metadata features (`prompt_length`, `tokens_out`).
-   **Extensibility.** Add a top-level `version`, and evolve with defaultable fields. Use schema registry to avoid producer/consumer drift.

---

## Partitioning and ordering

Partition by `tenant_id` (or `api_key_id` if tenants are huge). This ensures per-tenant ordering and keeps stateful windows colocated. A few practical tips:

-   **Hot keys**: If one tenant dominates, shard further by `tenant_id + hash(user_id)`. Maintain a mapping topic if you later need to re-join shards.
-   **Idempotency**: Enable idempotent producers and AT_LEAST_ONCE consumers; dedupe by `event_id` in your processor (e.g., RocksDB state keyed by `event_id` with TTL).
-   **Watermarks**: In Flink, set event-time watermarks (e.g., 2–5 minutes) to handle clock skew without exploding late events.

---

## Feature engineering in the stream

You’re not doing offline feature engineering; you’re computing features that are **cheap, causal, and windowed**. Examples:

-   **Rate features**: requests per minute (RPM), tokens per minute (TPM), error ratio.
-   **Burstiness**: ratio of max RPM in window to average RPM.
-   **Change points**: EWMA and z-score of `tokens_out` per request.
-   **Diversity**: unique `prompt_hash` cardinality (HLL sketch) vs. total requests (low diversity + high volume ⇒ automation).
-   **Geo/ASN drift**: distance between current ASN/geo and historical majority.
-   **Model mix**: distribution across `model`—sudden shift may indicate quota dodging.

These features are used by **rules** (thresholds) and/or **models** (anomaly detectors). Start with rules; add models once you have stable features.

---

## Detection recipes (copy-paste friendly)

### 1) Token burst (per key)

**Goal:** flag a sudden spike in token usage relative to baseline.

**Flink SQL**

```sql
CREATE TABLE calls (
  ts TIMESTAMP(3),
  api_key_id STRING,
  tokens_out BIGINT,
  WATERMARK FOR ts AS ts - INTERVAL '3' MINUTE
) WITH (...);

-- 5-minute sliding window with 1-minute slide
CREATE VIEW token_windows AS
SELECT
  TUMBLE_END(ts, INTERVAL '1' MINUTE) AS window_end,
  api_key_id,
  SUM(tokens_out) AS tpm
FROM TABLE(TUMBLE(TABLE calls, DESCRIPTOR(ts), INTERVAL '5' MINUTE))
GROUP BY api_key_id, window_start, window_end;

-- Join with a slowly-updated baseline (EWMA) held in a table
CREATE TABLE token_baseline (
  api_key_id STRING PRIMARY KEY,
  ewma_tpm DOUBLE
) WITH (...);

INSERT INTO detections
SELECT
  'token_burst' AS rule,
  api_key_id,
  window_end AS ts,
  tpm,
  ewma_tpm,
  CAST(tpm / NULLIF(ewma_tpm, 0) AS DOUBLE) AS multiple
FROM token_windows
JOIN token_baseline FOR SYSTEM_TIME AS OF token_windows.window_end
USING (api_key_id)
WHERE tpm > ewma_tpm * 5.0 AND tpm > 50000;
```

**Notes:** Maintain `token_baseline` by a side job that updates an EWMA per key hourly. The thresholds (`5×` and `50k`) are adjustable.

---

### 2) Geo-velocity & ASN mismatch

**ksqlDB**

```sql
CREATE STREAM calls WITH (...);

-- Derive country and ASN drift flags (assume enrichment produced country/asn)
CREATE TABLE home_context (
  api_key_id STRING PRIMARY KEY,
  home_country STRING,
  home_asn INT
) WITH (...);

CREATE STREAM geo_drift AS
  SELECT c.api_key_id, c.ts, c.geo_country, c.asn,
         CASE WHEN c.geo_country != hc.home_country THEN 1 ELSE 0 END AS country_drift,
         CASE WHEN c.asn != hc.home_asn THEN 1 ELSE 0 END AS asn_drift
  FROM calls c
  LEFT JOIN home_context hc
  ON c.api_key_id = hc.api_key_id
EMIT CHANGES;

CREATE TABLE drift_counts AS
  SELECT api_key_id, TUMBLINGWINDOW(SIZE 10 MINUTES) AS w,
         SUM(country_drift) AS country_hits,
         SUM(asn_drift) AS asn_hits
  FROM geo_drift
  WINDOW TUMBLING (SIZE 10 MINUTES)
  GROUP BY api_key_id;

CREATE STREAM detections AS
  SELECT 'geo_asn_drift' AS rule, api_key_id, WINDOWEND AS ts, country_hits, asn_hits
  FROM drift_counts
  WHERE country_hits >= 5 OR asn_hits >= 5
EMIT CHANGES;
```

**Notes:** Seed `home_context` from the first week’s majority location, updated slowly to avoid “learning” the attacker’s context too quickly.

---

### 3) Prompt spraying / jailbreaking signatures

You likely run a content filter that emits a boolean or score. Combine that with **low diversity + high velocity**.

**Kafka Streams (Java) snippet**

```java
KStream<String, CallEvent> calls = builder.stream("api.calls.v1",
    Consumed.with(Serdes.String(), callSerde));

KGroupedStream<String, CallEvent> byKey = calls.groupByKey();

TimeWindows w = TimeWindows.ofSizeWithNoGrace(Duration.ofMinutes(5)).advanceBy(Duration.ofMinutes(1));

KTable<Windowed<String>, SprayAgg> agg = byKey
  .windowedBy(w)
  .aggregate(
    SprayAgg::empty,
    (key, ev, a) -> a.add(ev), // adds count, violation_count, HLL on prompt_hash
    Materialized.<String, SprayAgg, WindowStore<Bytes, byte[]>>as("spray-store")
  );

KTable<Windowed<String>, Alert> alerts = agg
  .toStream()
  .filter((wk, a) -> a.violationRate() > 0.3 && a.uniquePrompts() < a.total() * 0.1 && a.total() > 100)
  .mapValues((wk, a) -> Alert.rule("prompt_spray", wk.key(), wk.window().end(), a.toMap()))
  .toTable();

alerts.toStream().to("detections.v1", Produced.with(windowedSerde, alertSerde));
```

**Notes:** The aggregate uses an HLL sketch to track unique `prompt_hash` cheaply.

---

### 4) Model mix misuse (quota dodging)

**Flink SQL**

```sql
CREATE VIEW model_mix AS
SELECT
  api_key_id,
  TUMBLE_END(ts, INTERVAL '5' MINUTE) AS window_end,
  COUNT(*) FILTER (WHERE model = 'gpt-4o') AS gpt4o_count,
  COUNT(*) FILTER (WHERE model = 'gpt-4o-mini') AS mini_count,
  COUNT(*) AS total
FROM TABLE(TUMBLE(TABLE calls, DESCRIPTOR(ts), INTERVAL '5' MINUTE))
GROUP BY api_key_id, window_start, window_end;

INSERT INTO detections
SELECT 'model_mix_spike', api_key_id, window_end,
       gpt4o_count, mini_count, total
FROM model_mix
WHERE gpt4o_count > 0 AND mini_count > 0 AND total > 100
  AND (gpt4o_count / NULLIF(total,0)) BETWEEN 0.45 AND 0.55;
```

**Rationale:** Attackers alternating models to dodge model-specific throttles produce suspicious near-50/50 mixes at high volume.

---

### 5) Output-dominant anomaly (possible exfiltration)

**Python asyncio micro-detector** (stateless, easy to iterate)

```python
import asyncio, json, math, time
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

ALERT_TOPIC = "detections.v1"
BOOTSTRAP = "kafka:9092"

# Keep per-key EWMA of output/input token ratio
ewma = {}
alpha = 0.05  # slow update to reflect typical behavior

def update_ewma(key, ratio):
    prev = ewma.get(key, ratio)
    v = alpha * ratio + (1 - alpha) * prev
    ewma[key] = v
    return v

async def run():
    consumer = AIOKafkaConsumer(
        "api.calls.v1",
        bootstrap_servers=BOOTSTRAP,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        enable_auto_commit=False,
        group_id="detector-output-dominant"
    )
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP,
                                value_serializer=lambda v: json.dumps(v).encode("utf-8"))
    await consumer.start(); await producer.start()
    try:
        async for msg in consumer:
            ev = msg.value
            ki = ev.get("api_key_id")
            tin = ev.get("tokens_in") or 1
            tout = ev.get("tokens_out") or 0
            ratio = tout / max(tin, 1)
            base = update_ewma(ki, ratio)
            # simple z-score with MAD-like scale
            dev = abs(ratio - base) / max(base, 1e-6)
            if tout > 2000 and dev > 3.0:
                alert = {
                    "rule": "output_dominant",
                    "api_key_id": ki,
                    "ts": ev["ts"],
                    "ratio": ratio,
                    "baseline": base,
                    "tokens_out": tout,
                }
                await producer.send_and_wait(ALERT_TOPIC, alert)
            await consumer.commit()
    finally:
        await consumer.stop(); await producer.stop()

asyncio.run(run())
```

**Notes:** This is intentionally simple; production versions maintain per-key baselines with TTL and handle rebalance safely.

---

## Stateful processing: windows, watermarks, and late data

It’s tempting to think “events arrive in order.” They don’t. Mobile networks, retries, multi-region replicas—expect **out-of-order** by seconds to minutes. That’s why stream processors use **event time** (embedded in the event) and **watermarks** (a moving lower bound that says “I’ve probably seen everything up to here”).

-   **Windows**: tumbling (fixed, non-overlapping), hopping/sliding (overlapping), and session (activity-bounded).
-   **Watermarks**: set to a conservatively large lateness (e.g., 3 minutes) to bound state size.
-   **Late events**: either drop with metrics or route to a `late.events.v1` topic for analysis.

State lives in RocksDB (Kafka Streams/Flink). Budget it. High-cardinality keys + long windows = state blowups. This is where partitioning discipline saves you.

---

## Concurrency & backpressure (and a quick detour into runtimes)

Streaming processors are event loops at scale. They pull from partitions, maintain state, and emit results. If your detector is Python, remember the **GIL**: a single process can run only one Python bytecode at a time. For IO-heavy workloads (Kafka poll/produce), **`asyncio`** performs well; for CPU-heavy (regex scanning, crypto), switch to processes or native extensions. JVM-based Flink/Kafka Streams handle concurrency for you with multi-threaded task slots.

Backpressure is how the system says “slow down”:

-   Kafka consumers control inflow via `max.poll.records` and commit pace.
-   Flink propagates backpressure through operators; observe it in metrics.
-   Don’t let detection block production traffic. **Never** put detectors inline with request handling; publish events asynchronously and make detections **advisory** with out-of-band controls.

---

## Enrichment joins: context turns signals into detections

Raw events are weak without context:

-   Tenant tier, trial flag, org size.
-   Known good IP ranges (office egress).
-   Key creation time.
-   Historical “home” ASN/geo.
-   Allow-lists for automated partners.

Implement enrichment via **streams-tables** joins:

-   CDC your `auth.users` and `auth.keys` into `auth.state.v1`.
-   In Kafka Streams, use a `GlobalKTable` for small reference data; in Flink, use a **broadcast state** pattern for low-latency joins.
-   Handle **slowly changing dimensions**: entries update rarely; version your records; mark stale.

---

## Privacy and compliance in a streaming world

-   **Redact at the edge**: Hash prompts before they hit Kafka. If you need NLP signals (toxicity, PII detection), compute them in the gateway and attach scores—not raw text.
-   **Separate clusters**: If raw content must be retained for an incident response, keep it in a short-retention, isolated cluster with audit logging.
-   **Minimize derived data**: Prefer sketches (HLL, Count-Min) to exact sets.
-   **Access**: Principle of least privilege for consumers; detections pipeline can read everything; analytics teams read only aggregated/feature topics.

---

## Operating the pipeline (a checklist)

1. **Schema Registry**: Required. Lock down compatibility to `BACKWARD` and lint schemas pre-merge.
2. **Observability**: Metrics for consumer lag, watermark delay, operator backpressure, state store size, and alert rate. Watch for **alert storms**.
3. **Cost controls**: Token usage correlates with $$; set budgets on retention and state size.
4. **Replay & testing**:

    - Keep a compacted `golden.events` topic with synthetic traces of known attacks.
    - Use Kafka Streams `TopologyTestDriver` or Flink MiniCluster for deterministic tests.
    - Replay into staging with a **time-shift** to validate windows and watermarks.

5. **Drift management**: Baselines (EWMA) update slowly to avoid “learning the attack.” Use hold-out periods for trials.
6. **Response playbooks**: Each detection should map to an action: human escalation, temporary throttle, key disable, or just log. Don’t invent the playbook during an incident.

---

## A minimal end-to-end example

Let’s wire a small pipeline: gateway → Kafka → Flink SQL → detection topic → throttle control.

**1) Gateway producer (pseudocode in Go)**

```go
type Event struct {
  EventID string `json:"event_id"`
  TS int64 `json:"ts"`
  TenantID string `json:"tenant_id"`
  APIKeyID string `json:"api_key_id"`
  IP string `json:"ip"`
  ASN int `json:"asn"`
  Geo string `json:"geo"`
  Endpoint string `json:"endpoint"`
  Model string `json:"model"`
  StatusCode int `json:"status_code"`
  LatencyMS int `json:"latency_ms"`
  TokensIn int `json:"tokens_in"`
  TokensOut int `json:"tokens_out"`
  SafetyViolation *bool `json:"safety_violation"`
  PromptHash string `json:"prompt_hash"`
  PromptLength int `json:"prompt_length"`
  CacheBypass *bool `json:"cache_bypass"`
  UserAgent string `json:"user_agent"`
  Version int `json:"version"`
}

// normalize and hash prompt server-side, don't forward raw prompt
```

**2) Flink SQL job for token bursts** (from earlier).

**3) Throttling control**: a tiny service reads `detections.v1`, decides whether to apply a temporary throttle, and writes to `controls.throttle.v1`:

```python
# throttle_control.py
import time, json
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

async def control_loop():
    c = AIOKafkaConsumer("detections.v1", bootstrap_servers="kafka:9092",
                         value_deserializer=lambda b: json.loads(b.decode()))
    p = AIOKafkaProducer(bootstrap_servers="kafka:9092",
                         value_serializer=lambda v: json.dumps(v).encode())
    await c.start(); await p.start()
    try:
        async for msg in c:
            d = msg.value
            if d["rule"] == "token_burst" and d["multiple"] > 10 and d["tpm"] > 200000:
                ctrl = {
                    "api_key_id": d["api_key_id"],
                    "ts": int(time.time()*1000),
                    "action": "throttle",
                    "rate_limit_rps": 1,       # clamp hard for 15min
                    "ttl_seconds": 900,
                    "reason": "auto-token-burst"
                }
                await p.send_and_wait("controls.throttle.v1", ctrl)
    finally:
        await c.stop(); await p.stop()
```

**4) Gateway applies control**: consume `controls.throttle.v1` and update an in-memory LRU per key. The main request path checks this throttle before forwarding to the LLM backend.

---

## Handling content signals without raw content

You can still detect prompt injection patterns without storing text:

-   Compute normalized regex flags _in the gateway_ (e.g., presence of “ignore previous”, “as an AI”, base64 blobs). Emit binary features like `regex_jb1=true`.
-   Include **character-class histograms** (`{alpha, digit, punctuation}` counts) and **Shannon entropy** approximations. Randomized cache-busters often show higher punctuation/digit ratios.
-   Use **MinHash** sketches of the prompt to estimate similarity across tenants without reconstructing the text.

These features are small, privacy-preserving, and powerful when combined with windows and baselines.

---

## When you add ML (and when you shouldn’t)

Rules cover 80% of value early on. Consider ML when:

-   You have enough labeled incidents to train supervised models (rare at first).
-   You need **cross-feature interactions** that are cumbersome as rules.

If you do:

-   Favor **online, incremental** methods (e.g., robust z-scores, EWMA, streaming isolation forests) over heavyweight batch retrains.
-   Store model state keyed by tenant to avoid “one size fits none.”
-   Guard with **circuit breakers**: never let a mis-tuned model throttle everyone. Keep manual allow-lists and privileged tenants.

---

## Common pitfalls

-   **Inline blocking**: Putting the detector synchronously in the request path. Latency gutters fill fast; you’ll DoS yourself.
-   **No watermarks**: Leads to unbounded state and nonsense windows.
-   **Assuming uniform keys**: Hot tenants break partitions and SLAs. Shard with intent.
-   **Unbounded alerts**: Alert storms during incidents can drown responders. Rate limit alerts per tenant and per rule.
-   **Learning the attacker**: Updating baselines too quickly after a shift bakes in the attack as “normal.”
-   **Schema drift**: Producers changing fields without compatibility checks. Use schema registry gates in CI.

---

## Historical aside: from single-threaded loops to planet-scale loops

If you’ve written `asyncio` or used Node’s event loop, you’ve seen the core pattern: events arrive, you react, you maintain a bit of state, and you move on. Streaming engines are that pattern industrialized. They add timestamp discipline, persistent state, windowing semantics, and fault tolerance. Where your local event loop juggles sockets, a streaming cluster juggles partitions, checkpoints, and watermarks. Same mental model—just… bigger.

---

## Putting it all together: a day in the life of a detection

1. A trial account’s key is pushed to GitHub. A bot picks it up.
2. The bot hits `/v1/chat/completions` from a new ASN with a ramping RPM.
3. Gateway emits events (prompt hashed, content redacted).
4. Kafka partitions by `api_key_id`; Flink jobs ingest with a 3-minute watermark.
5. Features compute: RPM up 8×, diversity low, safety violations 40%.
6. Two rules fire: `token_burst` and `prompt_spray`.
7. Throttle control writes a clamp to `controls.throttle.v1`.
8. Gateway applies a 1 rps limit; human on-call gets a neatly summarized alert.
9. After triage, the key is invalidated; baseline recovers; throttles expire automatically.

All without blocking business traffic or hand-parsing logs at 2am.

---

## Summary

-   **Behavior is the new perimeter.** Static checks can’t keep up with dynamic abuse of LLM and API endpoints.
-   **Events enable real-time defenses.** Kafka/Pulsar + Flink/Kafka Streams turn raw calls into windowed features, enriched with context, and detections that trigger timely actions.
-   **Schemas and privacy first.** Hash/fingerprint, don’t hoard content. Version your envelopes; enforce compatibility.
-   **Start with rules, add ML later.** Windowed counts, ratios, and simple baselines catch most issues. Bring models when you have data and guardrails.
-   **Operate like a systems engineer.** Watermarks, backpressure, state sizing, and replay testing matter as much as regexes.

If you build one thing this quarter, build your event envelope and wire a single token-burst detector. The first time it auto-throttles a leaked key, you’ll wonder how you lived without it.

---

## Further reading & practice prompts

-   **Stream processing internals:** Read about watermarks and event time semantics in Flink and Kafka Streams documentation; build a toy job with synthetic late events.
-   **Sketching for streaming:** HyperLogLog and Count-Min Sketch—great for diversity/uniqueness features.
-   **Security playbooks:** Define concrete actions per rule before you enable auto-controls.
-   **Experiment ideas:**

    1. Generate synthetic “spray” traffic and validate your prompt-spray recipe.
    2. Simulate geo-drift by replaying the same key from two IP ranges and measure detection latency.
    3. Create an online EWMA baseline per key and test how quickly it adapts after a true positive.

Happy streaming—and may your watermarks be timely and your alert storms short.
