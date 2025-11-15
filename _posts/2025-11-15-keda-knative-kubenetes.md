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
    overlay_image: /assets/images/keda-knative-kubenetes/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/keda-knative-kubenetes/banner.png
title: "KEDA vs. Knative vs. Kubernetes HPA: Choosing the Right Auto-Scaling Strategy for Microservices"
tags:
    - keda
    - knative
    - kubenetes
    - auto-scaling
---

Auto-scaling is the heartbeat of modern microservices. When it’s tuned well, your cluster feels alive: pods materialize as traffic surges, costs melt away when demand drops, and latency hugs your SLOs. When it’s tuned poorly, you get the opposite—thrash, cold starts, timeouts, and a creeping sense that the cluster is secretly your boss.

This post is a field guide to three pillars of Kubernetes scaling:

-   **HPA (Horizontal Pod Autoscaler)** — the built-in, resource-driven workhorse.
-   **KEDA** — event-driven scaling powered by external metrics and queue backlogs.
-   **Knative** — request-driven autoscaling for HTTP/GRPC with elegant scale-to-zero.

We’ll compare how they think about “load,” show realistic YAML you can paste into a cluster, and walk through hybrid patterns for latency-sensitive services. By the end, you’ll know when to pick each—and how to combine them without creating a hydra of competing HPAs.

---

## The Real Problem: What Are We Scaling _On_?

Before picking a tool, decide what signal represents “work” for your service. Different autoscalers optimize for different signals:

-   **CPU/Memory** — great when work is CPU-bound and steady. HPA’s home turf.
-   **Backlog/Events** — ideal when work is discrete (messages, jobs) and bursty. KEDA shines here.
-   **Concurrent Requests / RPS / Latency** — for interactive HTTP/GRPC where tail latency matters. Knative’s bread and butter.

Three more ideas frame our discussion:

1. **Reaction time vs. stability**: faster scaling reacts to spikes but risks oscillations. Slower scaling is stable but can blow SLOs.
2. **Scale-to-zero**: awesome for cost, tricky for latency due to cold starts.
3. **End-to-end capacity**: pod autoscaling is only half the story—cluster autoscaler, rate limits, and downstreams must keep up.

We’ll keep these trade-offs in mind as we dive into each system.

---

## Kubernetes HPA: The Default, for Good Reasons

**Mental model**: HPA watches metrics (CPU by default, plus custom metrics if configured) and adjusts replica counts to hit targets. It’s like a thermostat: “keep CPU ~70%.”

### How HPA Decides Replica Counts

For a resource metric (say, CPU utilization), the desired replica count is roughly:

```
desiredReplicas = ceil(currentReplicas * (currentMetric / targetMetric))
```

HPA v2 adds **multiple metrics**, scale-up/down **behaviors**, and **stabilization windows** to reduce thrash.

### When HPA Works Great

-   Services where **CPU tracks actual work** (e.g., CPU-bound compute, data transforms).
-   **Long-lived pods** where scale-up shouldn’t be hyper-reactive.
-   You want **no external dependencies** (no Prometheus adapter? no problem).

### HPA (v2) Example: CPU + Request Latency (via External Metric)

Suppose you expose a Prometheus histogram for request latency and surface a p90 gauge through a metrics adapter. You want to keep p90 ≤ 200ms but also respect CPU.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
    name: checkout-hpa
spec:
    scaleTargetRef:
        apiVersion: apps/v1
        kind: Deployment
        name: checkout
    minReplicas: 2
    maxReplicas: 50
    behavior:
        scaleUp:
            stabilizationWindowSeconds: 0
            policies:
                - type: Percent
                  value: 100 # at most double every 15s
                  periodSeconds: 15
        scaleDown:
            stabilizationWindowSeconds: 300 # wait 5m before scaling down
            policies:
                - type: Percent
                  value: 50
                  periodSeconds: 60
    metrics:
        - type: Resource
          resource:
              name: cpu
              target:
                  type: Utilization
                  averageUtilization: 70
        - type: External
          external:
              metric:
                  name: http_request_duration_p90_ms
              target:
                  type: AverageValue
                  averageValue: "200" # keep p90 around 200 ms
```

**Pros**

-   Native, simple, battle-tested.
-   Multi-metric support with v2.
-   Good for CPU-bound workloads.

**Cons**

-   Needs adapters to use custom/external metrics (latency, queue length).
-   **Not event-driven**: it won’t “wake up” on a queue spike unless you wire that metric in.
-   No built-in scale-to-zero.

**Use HPA when** CPU or a small set of metrics capture “work,” and you can tolerate warm baselines (minReplicas > 0).

---

## KEDA: Event-Driven Scaling (Queues, Schedules, Cloudy Things)

**Mental model**: KEDA bridges _external_ signals (Kafka lag, SQS depth, Redis list length, cron schedules, Prometheus queries, etc.) to pod scaling. It runs a controller + metrics server, creates an HPA **on your behalf**, and can **scale to zero** when there is no work.

### Why KEDA Exists

For queue-driven systems, “work” is the **backlog** and **arrival rate**—not CPU. If 50,000 messages land at once, you want pods _now_, even if current CPU is idle. KEDA polls the external system, calculates a desired replica count from triggers, and feeds that to an HPA it manages.

### KEDA ScaledObject Example: Kafka Lag

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
    name: orders-worker
spec:
    scaleTargetRef:
        kind: Deployment
        name: orders-worker
    minReplicaCount: 0 # allow scale-to-zero
    maxReplicaCount: 80
    pollingInterval: 5 # seconds
    cooldownPeriod: 300 # seconds
    advanced:
        horizontalPodAutoscalerConfig:
            behavior:
                scaleUp:
                    stabilizationWindowSeconds: 0
                    policies:
                        - type: Percent
                          value: 200
                          periodSeconds: 15
                scaleDown:
                    stabilizationWindowSeconds: 300
    triggers:
        - type: kafka
          metadata:
              bootstrapServers: kafka:9092
              consumerGroup: orders-cg
              topic: orders
              lagThreshold: "1000" # desired lag per replica
```

Interpretation: “Try to keep **~1000 messages of lag per replica**.” If lag is 50,000, KEDA asks for ~50 pods (subject to min/max). When lag is zero, it can **scale to zero**.

### KEDA Extras You’ll Actually Use

-   **ScaledJob**: scale **Jobs** by events (e.g., 1 Job per 100 messages).
-   **Multiple triggers**: e.g., Kafka lag _and_ a Prometheus rate.
-   **Fallbacks/behaviors**: guardrails when metric sources fail.
-   **Authentication** resources for cloud providers.

**Pros**

-   **Speaks queue** fluently; reacts to backlog.
-   **Scale-to-zero** without Knative.
-   Minimal changes to your app; no special HTTP sidecars.

**Cons**

-   KEDA owns the HPA it creates; **don’t attach a second HPA** to the same target.
-   Requires configuring triggers and (sometimes) credentials/adapters.
-   Backlog-based scaling may over-provision compute for small messages unless you tune thresholds.

**Use KEDA when** your work arrives via events/queues, or you need aggressive scale-to-zero for background workers.

---

## Knative: Request-Driven Autoscaling for HTTP/GRPC

**Mental model**: Knative Serving wraps your container in a **queue-proxy** and watches **concurrency and request rates**. It scales replicas to keep **in-flight requests per pod** near a target. It can also **scale to zero** and route cold traffic through an **activator** until pods are ready.

### Why Knative Feels Different

Knative’s signal is not CPU or backlog; it is **live request pressure**. That makes it ideal for **latency-sensitive** endpoints where you want to say, “Never let a pod juggle more than N concurrent requests.” Knative can also switch between:

-   **KPA (Knative Pod Autoscaler)** — concurrency/RPS-based.
-   **HPA class** — CPU-based scaling if you prefer.

### Knative Service Example: Concurrency-Based Autoscaling

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
    name: quotes
spec:
    template:
        metadata:
            annotations:
                autoscaling.knative.dev/metric: "concurrency"
                autoscaling.knative.dev/target: "50" # target in-flight reqs per pod
                autoscaling.knative.dev/window: "60s" # stable window
                autoscaling.knative.dev/panic-window-percentage: "10" # faster reaction
                autoscaling.knative.dev/panic-threshold-percentage: "200"
                autoscaling.knative.dev/minScale: "1" # avoid cold starts on baseline
                autoscaling.knative.dev/maxScale: "100"
        spec:
            containerConcurrency: 100 # hard cap per pod
            containers:
                - image: ghcr.io/acme/quotes:latest
                  ports:
                      - containerPort: 8080
```

**How it behaves** (simplified):

-   It estimates current concurrency across pods.
-   Desired replicas ≈ `observed_concurrency / target_concurrency`.
-   A **panic mode** reacts quickly to spikes (short window), then stabilizes using a longer window to avoid flapping.
-   If traffic drops to zero and `minScale` is 0, it **scales to zero** and later cold-starts via the activator.

**Pros**

-   Optimizes for **tail latency** on HTTP/GRPC.
-   Seamless **scale-to-zero** and traffic splitting by revision.
-   First-class concurrency controls and graceful cold-start handling.

**Cons**

-   Brings its own control plane (serving, activator, networking layer).
-   Best fit for HTTP-ish workloads; not a queue consumer.
-   Cold starts are real; you’ll often use `minScale` for critical paths.

**Use Knative when** you have interactive endpoints with strict latency SLOs, need revision traffic splitting, or want on-demand HTTP scale-to-zero.

---

## Side-by-Side: How They React to Metrics

| Dimension                        | HPA                                          | KEDA                                                        | Knative                                                      |
| -------------------------------- | -------------------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------ |
| **Primary signal**               | CPU/memory; custom & external (via adapters) | Event/queue backlog, rates, cron, Prometheus                | Concurrent requests, RPS; can optionally use CPU (HPA class) |
| **Scale-to-zero**                | Not native                                   | Yes (`minReplicaCount: 0`)                                  | Yes (`minScale: 0`, activator)                               |
| **Reaction speed**               | Moderate; configurable behaviors             | Fast (pollingInterval), but bounded by poll & HPA cool-down | Fast with panic window, then stable window                   |
| **Best for**                     | CPU-bound, steady workloads                  | Background workers, bursty event streams                    | Latency-sensitive HTTP/GRPC                                  |
| **Requires extra control plane** | No                                           | Small (operator + metrics server)                           | Larger (Knative Serving stack)                               |
| **Custom metrics complexity**    | Needs adapters                               | Built-in triggers/adapters                                  | Built-in request metrics                                     |

---

## The Math Behind Latency Targets (Quick Intuition)

If a single pod can handle **μ** requests/second at your SLO (e.g., measured at 50% CPU or at concurrency 50), and your incoming rate is **λ** requests/second, then a rough replica count is:

```
replicas ≈ ceil( λ / (μ * target_utilization) )
```

Knative bakes this into concurrency targets; HPA bakes it into CPU targets; KEDA translates queue length into “pods to drain backlog in time T.” If you know your **service time** and **arrival rate**, you can back into reasonable targets without pure guesswork.

---

## Hybrid Patterns for Latency-Sensitive Systems

Here’s where most teams get tangled: mixing autoscalers. The rule of thumb:

> **One owner per Deployment.** If KEDA generates an HPA for a Deployment, do not also attach your own HPA to it. If Knative owns scaling for a Service, don’t bolt on KEDA to the same pods.

You can still **compose** these systems by splitting responsibilities cleanly.

### Pattern 1: Knative for Ingress, KEDA for Background Work

A classic e-commerce “checkout” has two faces:

-   **HTTP API** (payment authorization, order placement) — latency-sensitive.
-   **Async pipeline** (invoice emails, fraud scoring, warehouse updates) — backlog-driven.

Use **Knative Service** for the API and **KEDA ScaledObject** for the worker.

```yaml
# API: Knative Service
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
    name: checkout-api
spec:
    template:
        metadata:
            annotations:
                autoscaling.knative.dev/metric: "concurrency"
                autoscaling.knative.dev/target: "40"
                autoscaling.knative.dev/minScale: "2" # keep warm
                autoscaling.knative.dev/maxScale: "60"
        spec:
            containers:
                - image: ghcr.io/acme/checkout:1.2.3
                  env:
                      - name: QUEUE_URL
                        value: "kafka://orders"
---
# Worker: KEDA ScaledObject on Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
    name: orders-worker
spec:
    replicas: 0 # KEDA will manage
    selector:
        matchLabels: { app: orders-worker }
    template:
        metadata:
            labels: { app: orders-worker }
        spec:
            containers:
                - name: worker
                  image: ghcr.io/acme/orders-worker:1.7.0
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
    name: orders-worker
spec:
    scaleTargetRef:
        kind: Deployment
        name: orders-worker
    minReplicaCount: 0
    maxReplicaCount: 100
    pollingInterval: 2
    cooldownPeriod: 180
    triggers:
        - type: kafka
          metadata:
              bootstrapServers: kafka:9092
              consumerGroup: orders-cg
              topic: orders
              lagThreshold: "2000"
```

**Why it works**: The API scales with live request pressure; the worker scales with backlog. Each has a single, clear owner.

**Latency tip**: set `minScale: 2` on the Knative Service to avoid customer-visible cold starts, and let the worker fluctuate from 0→N.

---

### Pattern 2: HPA for CPU + KEDA for a Separate Queue Adapter

You want to scale a CPU-bound **image transformer** on CPU, but also spike when a queue backlog grows. Avoid attaching both HPA and KEDA to the same Deployment. Instead:

-   Keep **image-transformer** scaled by HPA (CPU & maybe latency).
-   Add a **thin adapter** Deployment that pulls the queue and forwards to the transformer (e.g., through HTTP or NATS). Scale the adapter via KEDA on backlog.

```yaml
# CPU-driven transformer (HPA owner)
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
    name: img-hpa
spec:
    scaleTargetRef:
        apiVersion: apps/v1
        kind: Deployment
        name: img-transformer
    minReplicas: 2
    maxReplicas: 40
    metrics:
        - type: Resource
          resource:
              name: cpu
              target: { type: Utilization, averageUtilization: 75 }

---
# KEDA scales a separate adapter that fetches queue messages
apiVersion: apps/v1
kind: Deployment
metadata:
    name: img-adapter
spec:
    replicas: 0
    selector:
        matchLabels: { app: img-adapter }
    template:
        metadata:
            labels: { app: img-adapter }
        spec:
            containers:
                - name: adapter
                  image: ghcr.io/acme/img-adapter:2.1
                  env:
                      - name: TRANSFORMER_URL
                        value: "http://img-transformer:8080"
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
    name: img-adapter
spec:
    scaleTargetRef:
        kind: Deployment
        name: img-adapter
    minReplicaCount: 0
    maxReplicaCount: 100
    triggers:
        - type: redis
          metadata:
              address: redis:6379
              listName: transform-queue
              listLength: "500"
```

**Why it works**: two owners, two Deployments. The adapter increases request pressure on the transformer as backlog grows; HPA adds transformer replicas when CPU rises.

---

### Pattern 3: Knative with HPA Class (CPU) for “HTTP but CPU-Bound”

Your service is HTTP-facing but CPU is the real bottleneck (e.g., JSON → Parquet convertor). You want Knative’s routing/scale-to-zero but HPA’s CPU logic:

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
    name: parquetify
spec:
    template:
        metadata:
            annotations:
                autoscaling.knative.dev/class: "hpa.autoscaling.knative.dev"
                autoscaling.knative.dev/metric: "cpu"
                autoscaling.knative.dev/target: "75" # percent CPU
                autoscaling.knative.dev/minScale: "1"
                autoscaling.knative.dev/maxScale: "80"
        spec:
            containers:
                - image: ghcr.io/acme/parquetify:5.0.0
```

**Why it works**: Knative handles HTTP concerns and cold-starts; HPA semantics decide when to add pods.

---

### Pattern 4: HPA with External Latency Metric (No Knative)

You don’t want Knative, but you do care about **latency**. Expose a Prometheus metric for p90 and use an external metrics adapter:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
    name: api-hpa-latency
spec:
    scaleTargetRef:
        apiVersion: apps/v1
        kind: Deployment
        name: api
    minReplicas: 3
    maxReplicas: 60
    metrics:
        - type: External
          external:
              metric:
                  name: http_request_duration_p90_ms
              target:
                  type: AverageValue
                  averageValue: "150"
    behavior:
        scaleUp:
            stabilizationWindowSeconds: 0
            policies:
                - type: Percent
                  value: 100
                  periodSeconds: 15
        scaleDown:
            stabilizationWindowSeconds: 300
            policies:
                - type: Percent
                  value: 50
                  periodSeconds: 60
```

This keeps latency in check while staying within “just Kubernetes.”

---

## Tuning Without Tears: Practical Knobs That Matter

A few settings do most of the work.

### For HPA

-   **`behavior.scaleUp/scaleDown`**: shape your reaction curve. Aggressive scale-up, conservative scale-down is a sane default.
-   **`stabilizationWindowSeconds`**: prevents oscillation. Higher on scale-down.
-   **Multiple metrics**: combine CPU with one external metric instead of stacking HPAs.

### For KEDA

-   **`pollingInterval`**: lower for faster reaction, higher for fewer API calls.
-   **`cooldownPeriod`**: how long to wait before scaling down after last trigger.
-   **Trigger thresholds**: map **backlog per pod** to realistic processing throughput.
-   **`minReplicaCount`**: 0 for savings, >0 for warm workers.
-   **Avoid dual ownership**: let KEDA own the HPA for that Deployment.

### For Knative

-   **`autoscaling.knative.dev/target`**: concurrency target; measure your pod’s sweet spot.
-   **`containerConcurrency`**: hard cap to avoid head-of-line blocking.
-   **`minScale`**: keep a floor to avoid customer-visible cold starts.
-   **Panic vs. stable windows**: quicker spike reaction without long-term thrash.

---

## Common Pitfalls (and How to Dodge Them)

1. **Two HPAs, one Deployment**
   Don’t. If KEDA created an HPA, that’s the owner. Split the workload if you need two different scaling signals.

2. **Backlog target ignores message size**
   If your messages vary wildly, scale on **age of oldest message** or **processing time** instead of raw count, or normalize lag by expected bytes.

3. **Cold starts tank SLOs**
   Use `minScale` (Knative) or `minReplicaCount` (KEDA) ≥ 1 for critical paths. Consider **pre-warming** (periodic pings) for infrequent endpoints.

4. **Cluster autoscaler is asleep**
   Pod autoscaling can request 100 replicas faster than nodes can appear. Ensure **cluster autoscaler** quotas and **Pod Priorities** align with your SLO.

5. **Overfitting to synthetic tests**
   Load tests with perfect Poisson arrivals understate burstiness. Use production traces to set burst budgets and panic windows.

6. **Scaling on average, ignoring tails**
   If your SLO is p95 latency, don’t scale only on CPU mean. Either adopt Knative (concurrency) or surface a tail-latency metric to HPA.

---

## A Worked Example: Meeting a 200 ms p95 SLO

**Scenario**: An API averages 4 ms CPU time per request (nominal), but at concurrency > 60 per pod, GC and lock contention kick p95 above 200 ms. Traffic ranges from 50 rps to 3,000 rps within a minute.

**Knative approach**

-   Benchmark shows **sweet spot** at ~50 in-flight reqs per pod to keep p95 ≤ 200 ms.
-   Set `autoscaling.knative.dev/target: "50"`.
-   Keep `minScale: "2"` to avoid cold starts during off-hours.
-   Use `panic-window-percentage: "10"` to react within ~6s for spikes; long `window: 60s` to stabilize.

**Expected behavior**: At 3,000 rps, desired replicas ≈ 3,000 / 50 = 60 pods. Panic mode ramps quickly; stable window prevents oscillation as traffic wanes.

**HPA approach**

-   Export p90 as external metric and set `averageValue: "200"`.
-   Add CPU target at 70% as a secondary guard.
-   Aggressive scale-up (100% per 15s), conservative scale-down (50% per 60s, 5-minute stabilization).

**Trade-off**: HPA can work but you’re limited by metric freshness and adapter lag. Knative’s direct request signal reacts faster and more precisely for HTTP.

---

## Decision Flow: Picking the Right Tool

Ask three questions:

1. **How does work arrive?**

    - **HTTP/GRPC** → Start with **Knative** (concurrency/RPS).
    - **Queues/Events/Jobs** → Start with **KEDA** (backlog/age).
    - **CPU-bound batch/stream** → Start with **HPA** (CPU/memory).

2. **Do I need scale-to-zero?**

    - Yes (and HTTP) → **Knative**.
    - Yes (and queues) → **KEDA**.
    - No → **HPA** might be simplest.

3. **What’s my SLO?**

    - Tail latency → Prefer **Knative** or HPA with a tail-latency metric.
    - Cost/minimal control plane → Prefer **HPA**.
    - Bursty events → Prefer **KEDA**.

If two answers tie, split the workload into **two Deployments** and give each to its best-fit autoscaler. Fewer knobs per owner beats a mega-HPA with six metrics.

---

## Cheat-Sheet: Sensible Defaults

-   **HPA**

    -   CPU target: **70–75%**.
    -   Scale up: **max 100% / 15s**; scale down: **max 50% / 60s**, **5m stabilization**.
    -   Add one **external** metric if latency matters.

-   **KEDA**

    -   `pollingInterval`: **2–5s** for hot queues.
    -   `cooldownPeriod`: **180–300s**.
    -   Backlog target: `(expected rps * drain_time) / per_pod_rate`. Start conservative.
    -   `minReplicaCount`: **0** for workers unless SLO demands warm pods.

-   **Knative**

    -   `target` (concurrency): measured sweet spot per pod (commonly **30–100**).
    -   `minScale`: **1–2** for critical endpoints; **0** for low-traffic ones.
    -   Keep a **short panic window** and **longer stable window**.

---

## Summary: The Right Tool for the Right Signal

-   **HPA** is the sturdy default. If CPU tracks your real work (and you don’t need scale-to-zero), HPA is simple, native, and plenty capable—especially with v2 behaviors and external metrics.

-   **KEDA** turns external world signals into replicas. For queue-driven systems and background workers, it’s the most natural fit and gives you scale-to-zero without changing your app model.

-   **Knative** optimizes interactive latency by treating **concurrency** as the first-class signal. It’s the easiest way to keep p95 in check for HTTP/GRPC, with graceful scale-to-zero and traffic splitting.

For latency-sensitive microservices, the best setups are often **hybrid**: Knative for ingress paths, KEDA for background pipelines, HPA for CPU-bound transforms. Keep ownership clean—one autoscaler per Deployment—and tune a handful of behavior knobs. Your cluster (and your on-call rota) will thank you.

---

## Further Reading & Exploration

-   Kubernetes **Horizontal Pod Autoscaler v2** concepts and API.
-   **KEDA** documentation: triggers, ScaledObject, ScaledJob, and advanced HPA behavior.
-   **Knative Serving** autoscaling: KPA vs. HPA class, concurrency, activator, and scale-to-zero.
-   Kubernetes **Cluster Autoscaler**: ensuring node capacity keeps up with pod scale-ups.
-   “Monitoring-driven capacity planning”: building latency and throughput SLOs into autoscaling targets.

If you want, I can adapt the YAML snippets to your stack (Prometheus vs. Datadog, Kafka vs. SQS, etc.) and sketch a rollout plan that won’t surprise your cluster at 2 a.m.
