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
    overlay_image: /assets/images/predictive-scaling/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/predictive-scaling/banner.png
title: "Predictable Scaling: Reinventing Auto-Scaling with Queue Length, Traces, and Token Buckets"
tags:
    - predictive-scaling
    - hpa
    - auto-scaling
---

Most “auto-scaling” in the wild is basically:

> “If CPU > 70% for 5 minutes, add a pod.”

It _kind of_ works… until it really doesn't:

-   A GC pause spikes CPU and you over-scale.
-   A dependency slows down, latency explodes, but CPU is fine.
-   You get a burst of traffic, your queue explodes, autoscaler reacts late, and your SLOs die.

The common thread: CPU and memory are _machine-centric_ signals. But what you actually care about is _work_:

-   How many requests are waiting?
-   How fast are they arriving?
-   How long do they take to process?

In this post, we’ll walk through a different way to think about scaling:

> **Scale based on queue backlog and per-request cost (from traces), smoothed with a token bucket, to get deterministic, predictable elasticity.**

We’ll start from intuition, build up to a bit of math, then end with a concrete autoscaler sketch you could adapt to your own system.

---

## 1. Why CPU-based auto-scaling lies to you

Let’s start with what everyone’s already doing.

A typical autoscaling loop (HPA, EC2 ASG, etc.) looks roughly like:

```python
if avg_cpu > 0.7:
    replicas += 1
elif avg_cpu < 0.3 and replicas > min_replicas:
    replicas -= 1
```

Simple. But there are a bunch of problems:

1. **CPU doesn’t map directly to user experience.**
   Your users care about latency and errors, not whether your pods are “70% busy.”

2. **CPU is noisy.**

    - GC, JIT, TLS handshakes, encryption, compression…
    - A single “hot” pod can hide behind a nice average.

3. **Different requests cost different CPU.**
   A cheap cache hit and an expensive DB report look the same to “requests per second” metrics, but wildly different to CPU.

4. **You can’t reason about _backlog_.**
   “70% CPU” doesn’t tell you how many requests are waiting _right now_. It only tells you how busy the machines are.

The last point is the killer: you want to control **how long work waits**, not how your CPUs feel.

So let’s switch perspective.

---

## 2. From machines to work: thinking in queues

Imagine your system as a restaurant:

-   Requests are customers.
-   The queue is people waiting for a table.
-   Instances/pods are waiters.
-   Your “SLO” is “everyone should be seated within 2 minutes.”

What do you watch?

You don’t stare at the waiters’ heart rates.
You look at: **how many people are waiting and how fast the tables turn.**

That’s essentially:

-   **Arrival rate (λ)** – how many requests per second?
-   **Service time (W)** – how long does each request take to handle?
-   **Number of workers (C)** – how many replicas/threads processing work?

There’s a classic relationship from queuing theory (Little’s Law):

> **L = λ × W**
> Where:
> L = average number of items in the system (in-flight requests)
> λ = arrival rate
> W = average time in system (service + waiting)

We’re not going full grad-school math here, but this gives us a mental model:

-   You can’t make latency small if:

    -   arrival rate is higher than total processing capacity, or
    -   backlog is already huge compared to how fast you can drain it.

So instead of CPU, we want to scale on something like:

> **Backlog / capacity relative to a target latency.**

And the easiest place to measure _backlog_ is usually a **queue**.

### Where do queues live?

Common places:

-   Message queues (Kafka, SQS, Pub/Sub, RabbitMQ…)
-   HTTP reverse proxies with request queues
-   Thread pools / worker pools inside your app
-   Async task queues (Celery, Sidekiq, Resque, etc.)

Any place where requests are waiting to be processed is a gold mine for scaling signals.

---

## 3. Adding traces: how expensive is each request?

Knowing the backlog is half the story; we also need to know:

> How long does one unit of work take per replica?

You _could_ approximate this using histograms on your server (p95 latency, etc.), but if you already have distributed tracing, you get a nicer source of truth:

-   Each trace shows the lifetime of a request.
-   You can split out time spent _in a particular service_.
-   You can measure variability by endpoint, user, or tenant.

For now, let’s assume we can compute:

-   `avg_service_time` – average time spent actually processing a request in this service (not counting time stuck in upstream queues).

This gives us capacity per replica:

```text
capacity_per_replica ≈ 1 / avg_service_time   # requests per second for that replica
```

If `avg_service_time = 50ms = 0.05s`, then:

```text
capacity_per_replica ≈ 1 / 0.05 = 20 req/s
```

Now we know:

-   How many requests per second a single replica can process (roughly).
-   How many replicas we have.
-   How many requests are waiting (queue length).

We’re finally ready to build a **deterministic scaling rule**.

---

## 4. From SLO to replica count: a simple model

Let’s say we have:

-   `queue_length` – number of items currently waiting to be processed.
-   `arrival_rate` – recent smoothed rate of new items per second.
-   `avg_service_time` – average processing time per item.
-   `target_latency` – how long we’re okay with work waiting in the queue (e.g., 500ms).

We want to answer:

> How many replicas do we need so that:
>
> 1. we keep up with arrivals, and
> 2. we drain the backlog fast enough to keep queueing delay under target?

### Step 1: keep up with the arrival rate

Each replica can handle about:

```text
capacity_per_replica = 1 / avg_service_time
```

To handle arrivals:

```text
replicas_for_arrivals = ceil(arrival_rate / capacity_per_replica)
```

### Step 2: drain the backlog within target_latency

If we have `queue_length` items waiting and we want to clear them within `target_latency`, our required drain rate is:

```text
drain_rate = queue_length / target_latency   # items per second needed
```

That’s _additional_ capacity on top of arrivals (because new stuff is still coming in).

So:

```text
extra_replicas_for_backlog = ceil(drain_rate / capacity_per_replica)
```

### Step 3: combine and add some safety

```python
required_replicas = replicas_for_arrivals + extra_replicas_for_backlog
required_replicas = max(required_replicas, min_replicas)
required_replicas = min(required_replicas, max_replicas)
```

This model does something lovely:

-   If queue is empty and arrival rate is steady → scale to match traffic.
-   If queue starts growing → adds extra capacity proportional to how quickly you want to flush it.
-   If a big burst hits → you’ll jump capacity based on both increased arrivals _and_ backlog.

Let’s see this as code.

---

## 5. A toy autoscaler loop

Here’s a sketch in Python. This assumes we can pull metrics from somewhere (Prometheus, CloudWatch, your tracing system, etc.):

```python
import math
from dataclasses import dataclass
from time import sleep

@dataclass
class Metrics:
    queue_length: int         # items waiting in queue
    arrival_rate: float       # items/second (smoothed)
    avg_service_time: float   # seconds per item
    current_replicas: int

@dataclass
class Config:
    target_latency: float     # seconds of acceptable queueing delay
    min_replicas: int = 1
    max_replicas: int = 100
    scale_up_sensitivity: float = 1.0   # multipliers to tune aggressiveness
    scale_down_sensitivity: float = 0.5

def compute_desired_replicas(metrics: Metrics, cfg: Config) -> int:
    if metrics.avg_service_time <= 0:
        # fallback: avoid division by zero
        return metrics.current_replicas

    capacity_per_replica = 1.0 / metrics.avg_service_time

    # 1) replicas needed just to keep up with new arrivals
    replicas_for_arrivals = metrics.arrival_rate / capacity_per_replica

    # 2) replicas to drain the backlog within the target latency
    drain_rate = metrics.queue_length / max(cfg.target_latency, 1e-3)
    extra_replicas_for_backlog = drain_rate / capacity_per_replica

    raw_required = replicas_for_arrivals + extra_replicas_for_backlog

    # Tune aggressiveness on scale up vs scale down
    if raw_required > metrics.current_replicas:
        scaled_required = raw_required * cfg.scale_up_sensitivity
    else:
        scaled_required = raw_required * cfg.scale_down_sensitivity

    desired = math.ceil(scaled_required)

    # clamp to bounds
    desired = max(desired, cfg.min_replicas)
    desired = min(desired, cfg.max_replicas)

    return desired

def autoscaler_loop(fetch_metrics, apply_scale, cfg: Config, period_s: int = 30):
    while True:
        metrics = fetch_metrics()
        desired = compute_desired_replicas(metrics, cfg)

        if desired != metrics.current_replicas:
            print(f"[autoscaler] scaling from {metrics.current_replicas} -> {desired}")
            apply_scale(desired)
        else:
            print(f"[autoscaler] staying at {metrics.current_replicas} replicas")

        sleep(period_s)
```

So far this will already outperform CPU-based autoscaling in many systems. But it’s still a bit _twitchy_:

-   Traffic is bursty.
-   Measurements are noisy.
-   You might wind up adding/removing replicas too often.

Time to bring in a classic: **token buckets**.

---

## 6. Token buckets: taming the flappy autoscaler

Token buckets are usually used for **rate limiting**:

-   Tokens are added to a bucket at a fixed rate.
-   Each action consumes a token.
-   If there are no tokens, you can’t do the action.

We can use exactly the same idea to **rate limit scaling changes**.

### Why do we need this?

Even with a solid model, you don’t want to:

-   Scale up and down every 30 seconds.
-   React to every minor jitter in arrival rate or queue length.

We want:

1. Quick reaction to _real_ spikes (your backlog jumps).
2. Inertia against short-lived blips.

A token bucket gives us a nice, explicit control:

> “We are allowed to scale up by at most N replicas per minute and scale down by at most M replicas per minute.”

### Scaling with a token bucket

We’ll maintain two buckets:

-   `scale_up_bucket`
-   `scale_down_bucket`

Each bucket:

-   Has a capacity (max tokens).
-   Refills at a fixed rate (tokens per second).
-   Spending tokens allows us to perform scale actions.

Let’s extend our loop:

```python
import time

@dataclass
class TokenBucket:
    capacity: float
    fill_rate: float   # tokens per second
    tokens: float = 0.0
    last_refill_ts: float = time.time()

    def refill(self):
        now = time.time()
        delta = now - self.last_refill_ts
        self.last_refill_ts = now
        self.tokens = min(self.capacity, self.tokens + delta * self.fill_rate)

    def consume(self, amount: float) -> bool:
        self.refill()
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False
```

Now modify `autoscaler_loop`:

```python
def autoscaler_loop(fetch_metrics, apply_scale, cfg: Config, period_s: int = 30):
    scale_up_bucket = TokenBucket(capacity=10, fill_rate=1.0)     # e.g. 1 "scale unit" per second
    scale_down_bucket = TokenBucket(capacity=10, fill_rate=0.5)   # slower downscaling

    while True:
        metrics = fetch_metrics()
        desired = compute_desired_replicas(metrics, cfg)

        delta = desired - metrics.current_replicas

        if delta > 0:
            # need to scale up
            if scale_up_bucket.consume(delta):
                print(f"[autoscaler] scaling UP by {delta}: {metrics.current_replicas} -> {desired}")
                apply_scale(desired)
            else:
                print(f"[autoscaler] scale-up throttled; not enough tokens")
        elif delta < 0:
            # need to scale down
            amount = abs(delta)
            if scale_down_bucket.consume(amount):
                print(f"[autoscaler] scaling DOWN by {amount}: {metrics.current_replicas} -> {desired}")
                apply_scale(desired)
            else:
                print(f"[autoscaler] scale-down throttled; not enough tokens")
        else:
            print(f"[autoscaler] staying at {metrics.current_replicas} replicas")

        time.sleep(period_s)
```

Now we’ve got three layers of control:

1. **Deterministic math** from queues, traces, and SLO.
2. **Aggressiveness knobs** via `scale_up_sensitivity` and `scale_down_sensitivity`.
3. **Hard rate limits** via token buckets.

Together, they give you **predictable elasticity**:

-   You can estimate worst-case scaling speed.
-   You can bound cost explosions (no “added 200 pods in 30s” by accident).
-   You can explain scaling decisions to humans (“queue jumped to 10k, we had 10 scale-up tokens, so we added 10 replicas this minute”).

---

## 7. Where do metrics actually come from?

So far we’ve hand-waved `fetch_metrics`. In a real system, you’d stitch this together from:

### Queue length

-   **Message queues**: `ApproximateNumberOfMessages` (SQS), lag (Kafka), etc.
-   **HTTP queues**: some proxies expose current request backlog per upstream.
-   **Worker queues**: your app can expose “in-flight tasks” via a metric.

### Arrival rate

Calculate using a sliding window:

-   Count items enqueued per interval (e.g., per 10 seconds).
-   Use an exponentially weighted moving average (EWMA) to smooth.

```python
class EWMA:
    def __init__(self, alpha: float):
        self.alpha = alpha
        self.value = None

    def update(self, x: float):
        if self.value is None:
            self.value = x
        else:
            self.value = self.alpha * x + (1 - self.alpha) * self.value
        return self.value
```

### Average service time (from traces)

If you have tracing (OpenTelemetry, Jaeger, etc.):

-   Filter spans for your service.
-   Measure duration of the span that corresponds to the processing of a unit of work.
-   Compute a rolling average or p90.

If not, you can approximate from server-side latency histograms (e.g. from your HTTP handler), but be careful to exclude time waiting in _your_ queue if you’re already measuring that separately.

---

## 8. Failure modes and edge cases

Nothing is magic. Let’s talk about where this approach can still hurt you—and how to mitigate it.

### 1. Highly variable request cost

If some requests are 1ms and others are 2s, a single `avg_service_time` is garbage.

Options:

-   Maintain service times **per queue / topic / route** and scale each independently.
-   Use **p90** or p95 instead of mean (careful: this can make your capacity estimate more conservative).

### 2. Cold starts and warm-up time

If a new replica takes 30 seconds to become ready, your theoretical “we can drain queue in 500ms” is optimistic.

Mitigations:

-   Include **startup time** as an extra safety margin.
-   Overprovision slightly: e.g. `required_replicas * 1.2`.
-   Tune token bucket fill rates so you don’t commit to a huge scaling jump all at once if your platform’s cold starts are slow.

### 3. Measuring “the right queue”

If you scale based on one queue but the real bottleneck is elsewhere, you’ll chase ghosts.

Example:

-   You scale the API based on HTTP backlog.
-   But the real problem is a shared DB that can’t keep up.

You’ll happily add API pods and just hammer the DB harder.

Mitigations:

-   Combine **queue metrics** with **downstream health indicators** (errors, saturation).
-   Scale the part of the system that’s truly bottlenecked (often a worker pool, not the API edge).

### 4. Metrics lag and sampling

If your arrival rate and service time come from different aggregation windows, you can get weird interactions.

Best practice:

-   Use similar time windows for all three: queue length (instant), arrival rate (last 30–60 seconds), service time (last 5–10 minutes).
-   Be explicit about the windows when reasoning about SLOs.

---

## 9. Putting it all together: a mental recipe

Let’s recap the design as a step-by-step recipe you can adapt.

### Step 1: Define the SLO in terms of queueing

Example:

> 95% of jobs should start processing within **500ms** of being enqueued.

That’s your `target_latency`.

### Step 2: Instrument queues and traces

-   Export `queue_length` as a metric.
-   Export `arrival_rate` (EWMA).
-   Export `avg_service_time` (or p90) using tracing or latency histograms.

### Step 3: Compute desired capacity

In your autoscaler:

```text
capacity_per_replica = 1 / avg_service_time

replicas_for_arrivals      = arrival_rate / capacity_per_replica
extra_replicas_for_backlog = (queue_length / target_latency) / capacity_per_replica

raw_required = replicas_for_arrivals + extra_replicas_for_backlog
```

Then apply:

-   Clamp to `[min_replicas, max_replicas]`.
-   Adjust up/down sensitivities.

### Step 4: Smooth with a token bucket

-   Maintain separate buckets for scale up / scale down.
-   Each scaling action spends tokens proportional to the number of replicas changed.
-   Token fill rates define your maximum rate of change.

### Step 5: Verify against reality

Run this model in **shadow mode** first:

-   Don’t actually scale anything; only log what the autoscaler _would_ have done.
-   Compare predicted replica counts vs actual CPU/latency over time.
-   Adjust parameters until the actions look sane.

Once happy, wire it into your orchestrator (Kubernetes, ECS, Nomad, home-grown, etc.) as an internal controller or external autoscaler.

---

## 10. Why this feels different in practice

When you move from “CPU > 70%” to “queue length, traces, and token buckets,” a few things change in how scaling _feels_:

1. **Scaling conversations become about work, not machines.**

    - “We need to handle 2000 jobs/s with 200ms queueing delay”
      instead of
    - “We should probably bump the CPU target to 60%?”

2. **You can reason about worst-case behavior.**

    - Given an arrival burst and your token bucket config, you know how fast capacity ramps.

3. **Changes are explainable and auditable.**
   A scale event isn’t “CPU spiked ¯\*(ツ)\*/¯” but
   “queue jumped from 500 to 5000, arrival rate doubled, service time stayed stable, so we added 15 replicas to keep queueing delay under 500ms.”

4. **You get deterministic elasticity.**
   It becomes possible to simulate:

    - “What if traffic doubles?”
    - “What if service time regresses by 30%?”
    - “What if we lower the SLO to 200ms?”

Because the model is explicit, you can run those what-ifs as math, not guesswork.

---

## 11. Further reading and ideas

If this approach resonates, here are some directions to dive deeper:

-   **Queueing theory basics** – Little’s Law, M/M/1 queues, and how they relate to latency.
-   **KEDA and event-driven autoscaling** – many real systems already scale based on queue depth; you can layer in traces and token buckets on top.
-   **Distributed tracing internals** – how span timing and sampling affects your view of service time.
-   **Control theory** – PID controllers and how they compare to token-bucket-style rate limiting for autoscalers.

---

Auto-scaling doesn’t have to be a mysterious box that sometimes helps and sometimes ruins your day.

If you start from _work_—queue lengths and per-request cost—and then control _how aggressively_ you act on that signal with token buckets, you get something much nicer:

> **Scaling that’s predictable, explainable, and directly tied to the thing you actually care about: how long your users’ work waits.**
