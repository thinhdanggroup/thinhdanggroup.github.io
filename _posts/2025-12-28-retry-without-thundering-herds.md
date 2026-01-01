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
    overlay_image: /assets/images/retry-without-thundering-herds/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/retry-without-thundering-herds/banner.png
title: "Retries Without Thundering Herds"
tags:
    - retry
    - control plane
---

## Retry budgets, jitter strategies, and queue backpressure for control‑plane operations

At 02:13, your control plane sneezes.

Maybe it’s an API server rolling. Maybe it’s an etcd hiccup. Maybe a dependency starts returning `429 Too Many Requests` because it’s having a bad day and would like everyone to calm down.

Your operators, controllers, reconcilers, and “helpful little automation friends” all notice at the same time. They all do the responsible thing: **retry**.

And that’s when the outage gets… louder.

A control plane is the part of your system that _decides_ what the world should look like (desired state) and _pushes_ the world toward it (actual state). It’s also the part where a single transient failure can trigger retries across hundreds or thousands of processes. Those retries turn a small dip into a full-on synchronized stampede: the classic **thundering herd**.

This post is about building retry behavior that _actually helps_ during failures, instead of “helping” like a toddler helps you clean the kitchen (enthusiastically, but now everything is sticky).

We’ll focus on three tools that work best together:

1. **Retry budgets**: a fuse that prevents retry amplification.
2. **Jitter strategies**: randomness that prevents synchronization.
3. **Queue backpressure**: admission control so you don’t create more work than downstream can handle.

Along the way we’ll write small, commented code snippets you can adapt to your own clients/controllers.

---

## The failure mode: when “retry” becomes “attack”

Let’s start with a very normal piece of code:

```python
import time

def retry_forever(call):
    delay = 1.0
    while True:
        try:
            return call()
        except Exception:
            time.sleep(delay)
            delay = min(delay * 2, 30.0)  # capped exponential backoff
```

This looks reasonable: exponential backoff, cap at 30 seconds, no hot-looping. Great!

Now imagine:

-   500 controllers start at once (deploy, node reboot, leader election, whatever).
-   They all attempt the same control-plane write.
-   The backend returns `503` for 10 seconds.
-   Every controller enters this exact retry loop with the same timing.

Exponential backoff **reduces frequency**, but it can still create **clusters**: everyone sleeps ~1s, then everyone wakes; everyone sleeps ~2s, then everyone wakes; and so on. AWS’s analysis of exponential backoff shows these retry calls still occur in spikes (“clusters of calls”) without jitter, even though they happen less often. ([Amazon Web Services, Inc.][1])

Control planes amplify this because they have:

-   **High fan-out**: many independent clients reacting to the same failure.
-   **Shared chokepoints**: API servers, consensus stores, rate-limited endpoints.
-   **Feedback loops**: failing writes cause more reconciliation, which causes more writes.

So the fix isn’t “don’t retry.” The fix is: **retry with coordination, randomization, and admission control.**

### Section summary

-   Exponential backoff alone often still synchronizes retries into spikes. ([Amazon Web Services, Inc.][1])
-   Control planes are especially susceptible because many actors observe the same failures simultaneously.

---

## A useful mental model: decide, schedule, admit

Retries have three separate decisions hiding inside them:

1. **Decide**: _Should I retry at all?_ (Is the error retryable? Is the operation safe to repeat?)
2. **Schedule**: _When should I retry?_ (Backoff + jitter)
3. **Admit**: _Am I allowed to send this retry right now?_ (Budgets, rate limits, queues)

Most “retry logic” only handles #2, and usually only halfway. Control-plane reliability comes from handling all three.

We’ll tackle them in order, then combine them into a pattern you can drop into a controller or client.

---

## Retry budgets: a fuse for retry storms

A retry budget is a deliberately boring idea with surprisingly powerful consequences:

> You don’t get unlimited retries. You get a _budget_.

The key is that the budget is tied to **normal traffic**, so that when normal traffic stops (because everything is failing), the budget drains and retries self-limit.

Twitter’s Finagle defines a `RetryBudget` abstraction with three core operations: a `deposit()` (credit), a `tryWithdraw()` (spend a retry), and a way to inspect `balance`.

In other words: successful (or at least “attempted”) work deposits credits; retries withdraw credits. If you’re in a world where everything fails, you stop depositing credits, so you quickly stop retrying.

### How big should the budget be?

Finagle’s `RetryBudget.apply(...)` is explicitly designed to allow a configurable percentage of requests to be retried over a time window (`ttl`), plus a minimum retry rate for low-traffic clients (`minRetriesPerSec`). It even gives the intuition: `percentCanRetry = 0.1` means “for every 10 deposits, 1 retry is allowed.”

That “percentage of traffic” framing is the important part.

If you let retries add 100% more load during an outage, you haven’t added resilience—you’ve added a multiplier. If you cap retries to, say, **10–20% extra** load, you’ve basically installed a fuse that says: “I will try a bit harder… but I will not burn the building down.”

Google’s SRE book describes a similar idea in overload handling: they use both a **per-request retry cap** (e.g., up to three attempts) and a **per-client retry budget** that keeps retries below a fraction of overall requests (they mention 10% as a rationale). ([Google SRE][2])

### A tiny retry budget you can implement in an afternoon

Here’s a simple sliding-window retry budget inspired by those ideas. It isn’t production-hardened, but it’s _very_ workable.

```python
import time
import threading
from collections import deque

class RetryBudget:
    """
    Sliding-window retry budget:
    - Each "deposit" represents one normal request (or one successful request, depending on your policy).
    - We allow:
        * min_retries_per_sec * ttl_seconds retries as a baseline reserve
        * plus percent_can_retry * deposits_in_window retries
    - Each retry attempt records a "withdrawal" timestamp.
    - Deposits and withdrawals expire after ttl_seconds.
    """
    def __init__(self, ttl_seconds: float, min_retries_per_sec: float, percent_can_retry: float):
        if ttl_seconds < 1.0:
            raise ValueError("ttl_seconds should be >= 1s for stability")
        if min_retries_per_sec < 0:
            raise ValueError("min_retries_per_sec must be >= 0")
        if percent_can_retry < 0:
            raise ValueError("percent_can_retry must be >= 0")

        self.ttl = ttl_seconds
        self.min_rps = min_retries_per_sec
        self.pct = percent_can_retry

        self._deposits = deque()    # timestamps
        self._withdrawals = deque() # timestamps
        self._lock = threading.Lock()

    def _expire_old(self, now: float) -> None:
        cutoff = now - self.ttl
        while self._deposits and self._deposits[0] < cutoff:
            self._deposits.popleft()
        while self._withdrawals and self._withdrawals[0] < cutoff:
            self._withdrawals.popleft()

    def deposit(self) -> None:
        now = time.time()
        with self._lock:
            self._expire_old(now)
            self._deposits.append(now)

    def balance(self) -> float:
        now = time.time()
        with self._lock:
            self._expire_old(now)
            allowed = (self.min_rps * self.ttl) + (self.pct * len(self._deposits))
            spent = len(self._withdrawals)
            return max(0.0, allowed - spent)

    def try_withdraw(self) -> bool:
        now = time.time()
        with self._lock:
            self._expire_old(now)
            allowed = (self.min_rps * self.ttl) + (self.pct * len(self._deposits))
            if len(self._withdrawals) < allowed:
                self._withdrawals.append(now)
                return True
            return False
```

A few practical notes:

-   **What counts as a deposit?**

    -   In some systems, you deposit on _every request attempt_ (success or fail).
    -   In others, you deposit on _success_ only, so budgets shrink under failure faster.
        Both are valid; choose based on how aggressively you want to clamp down.

-   **`min_retries_per_sec` is for bootstrapping.**
    Without it, a brand-new controller that hasn’t had deposits yet may never retry. Finagle includes a reserve specifically for low-traffic scenarios.

-   **Still cap per-request attempts.**
    A retry budget limits _aggregate_ retries. You still want a simple per-operation cap (like “try at most 3–5 times”) so a single call doesn’t linger forever.

### Section summary

-   Retry budgets prevent retry amplification by tying retries to a “percent of normal traffic.”
-   Combine per-request attempt caps with per-client/process retry ratios to avoid storms. ([Google SRE][2])

---

## Jitter strategies: break synchronization (on purpose)

Backoff answers “retry less frequently.”
**Jitter** answers “retry at _different times_ than everyone else.”

AWS’s write-up shows why this matters: even with exponential backoff, retries still happen in clusters; adding jitter spreads calls into an “approximately constant rate” instead of spikes. ([Amazon Web Services, Inc.][1])

There are a few common jitter strategies, and the differences matter most when many clients fail together.

### The backoff building block

Start with a capped exponential backoff duration:

```python
def exp_backoff(base: float, cap: float, attempt: int) -> float:
    # attempt=0 -> base
    # attempt=1 -> 2*base
    # ...
    return min(cap, base * (2 ** attempt))
```

Then apply jitter.

### Full jitter

Pick a random value between 0 and the current backoff ceiling.

```python
import random

def full_jitter(base: float, cap: float, attempt: int) -> float:
    b = exp_backoff(base, cap, attempt)
    return random.uniform(0.0, b)
```

This is often the best default in high fan-out failure scenarios. It aggressively de-synchronizes.

### Equal jitter

Always wait at least half the backoff, then add randomness for the remaining half.

```python
def equal_jitter(base: float, cap: float, attempt: int) -> float:
    b = exp_backoff(base, cap, attempt)
    return (b / 2.0) + random.uniform(0.0, b / 2.0)
```

AWS’s analysis compares multiple jitter strategies and calls “equal jitter” the loser among jittered approaches in their simulation. ([Amazon Web Services, Inc.][1])
That doesn’t mean it’s _always_ wrong—but it does mean you should have a reason before choosing it.

### Decorrelated jitter

Instead of strictly doubling each time, you randomize based on the previous sleep. This avoids “sticky” synchronization patterns.

```python
def decorrelated_jitter(base: float, cap: float, prev_sleep: float) -> float:
    # Typical form: sleep = min(cap, random(base, prev_sleep * 3))
    return min(cap, random.uniform(base, prev_sleep * 3.0))
```

AWS describes “decorrelated jitter” as a variant where the max jitter depends on the last value. ([Amazon Web Services, Inc.][1])

### Don’t retry unsafe operations

Jitter and budgets won’t save you if you retry operations that _shouldn’t_ be retried.

Google’s retry guidance explicitly recommends using exponential backoff _with jitter_ for retryable, idempotent operations—and calls out anti-patterns like retrying non-idempotent operations and retrying without backoff. ([Google Cloud Documentation][3])

In control planes, a lot of operations are idempotent by design (reconciliation should converge), but not all are. Examples that can bite you:

-   “Create if not exists” without a stable idempotency key.
-   “Increment counter.”
-   “Append to list.”
-   “Send notification.”

When in doubt: make the operation idempotent (use resource versions, etags, request IDs), or don’t retry automatically.

### Section summary

-   Jitter turns retry spikes into a smoother stream under correlated failures. ([Amazon Web Services, Inc.][1])
-   Full jitter is a strong default; decorrelated jitter is a good alternative; equal jitter often underperforms. ([Amazon Web Services, Inc.][1])
-   Only retry operations you can safely repeat; don’t blindly retry non-idempotent actions. ([Google Cloud Documentation][3])

---

## Queue backpressure: stop generating infinite work

Retries aren’t the only herd problem.

Control-plane components often run event loops:

-   watch events come in (resource changes, heartbeats, config updates),
-   enqueue reconcile work,
-   workers process items,
-   processing may call the API (read/write),
-   failures enqueue more work (retry / requeue).

If the API gets slow, naïve designs do something like:

> “Work is piling up! Quick! Create more goroutines!”

That’s not backpressure—that’s denial.

### The “workqueue” pattern: coalesce + limit + requeue

Kubernetes popularized a really solid approach: a queue that is:

-   **Fair**: process in order added,
-   **Stingy**: don’t process the same item concurrently; coalesce duplicates,
-   supports multiple producers/consumers and allows re-enqueue while processing. ([pkg.go.dev][4])

That “stingy” property is huge for control planes because it prevents _hot keys_ from melting your worker pool.

Kubernetes also ships a default controller rate limiter that combines:

-   an **overall token bucket** limiter, and
-   a **per-item exponential backoff** limiter. ([pkg.go.dev][4])

Even the rate limiter implementation descriptions are blunt: the item exponential limiter is basically `baseDelay * 2^numFailures`. ([pkg.go.dev][4])

Translation: **backpressure is not an afterthought. It’s part of the core loop.**

### A minimal coalescing queue (conceptual)

Here’s a stripped-down queue that coalesces duplicate keys and prevents concurrent processing of the same key.

```python
import threading
from collections import deque

class CoalescingQueue:
    """
    A toy "workqueue":
    - add(key): enqueue only if not already queued
    - get(): blocks until an item is available
    - done(key): marks completion
    Not production-ready, but demonstrates 'stingy' de-dup behavior.
    """
    def __init__(self):
        self._q = deque()
        self._queued = set()
        self._cv = threading.Condition()

    def add(self, key):
        with self._cv:
            if key in self._queued:
                return  # coalesce duplicates
            self._queued.add(key)
            self._q.append(key)
            self._cv.notify()

    def get(self):
        with self._cv:
            while not self._q:
                self._cv.wait()
            return self._q.popleft()

    def done(self, key):
        with self._cv:
            self._queued.discard(key)
```

This is the essence of “stingy”: if 50 events happen for the same object while you’re busy, you still only reconcile it once more, not 50 times.

### Backpressure knobs that matter in practice

In a control plane, you typically need **at least** these:

1. **Bounded concurrency**
   A worker pool (N threads / goroutines) or a semaphore that caps in-flight operations.

2. **Bounded queues (or deliberate coalescing)**
   If your queue is unbounded and downstream is down, memory becomes your “buffer.” That ends badly.

3. **Rate limiting / token bucket for outbound calls**
   Especially for shared API servers. Your own worker pool is not enough if each worker can hammer the backend at full speed.

4. **Per-key backoff**
   If one resource is broken (bad config), don’t requeue it as fast as healthy resources.

5. **Global retry budget**
   If _everything_ is broken, stop retrying quickly and let the system breathe.

### Section summary

-   Backpressure turns “infinite work generation” into controlled admission.
-   Coalescing queues avoid hot-key meltdowns; rate limiters and worker pools protect the backend. ([pkg.go.dev][4])

---

## Putting it together: a “retrying reconciler” loop

Let’s wire these ideas into a coherent control-plane loop.

Assume we have:

-   a queue of reconcile keys,
-   a fixed worker pool,
-   a retry budget,
-   a jittered backoff policy,
-   an outbound token bucket (optional but recommended).

### Step 1: classify errors and enforce idempotency

A basic classification function (very simplified):

```python
def is_retryable(error: Exception) -> bool:
    # In real systems you’d check types / status codes:
    # - 408, 429, 5xx
    # - connection resets, timeouts
    # And exclude:
    # - 4xx (except 408/429), validation errors, auth errors, etc.
    return True
```

Also: ensure reconcile operations are idempotent. If your “write” uses optimistic concurrency (resource versions/etags), retries are far safer.

AWS’s blog post is actually about optimistic concurrency control contention and how backoff + jitter reduces waste under contention. ([Amazon Web Services, Inc.][1])
Control planes live in this world.

### Step 2: a retry wrapper that uses both budget and jitter

```python
import time

class RetryExhausted(Exception):
    pass

def call_with_budgeted_retries(
    call,
    budget: RetryBudget,
    *,
    max_attempts: int = 4,
    base: float = 0.2,
    cap: float = 10.0,
):
    """
    - Deposits once per *top-level* operation.
    - Withdraws for each retry attempt.
    - Uses full jitter to avoid sync spikes.
    """
    budget.deposit()

    for attempt in range(max_attempts):
        try:
            return call()
        except Exception as e:
            if attempt == max_attempts - 1:
                raise

            if not is_retryable(e):
                raise

            # Retry budget admission control
            if not budget.try_withdraw():
                raise RetryExhausted("retry budget exhausted; failing fast") from e

            # Jittered backoff scheduling
            sleep_s = full_jitter(base, cap, attempt)
            time.sleep(sleep_s)
```

This gives you:

-   **A per-operation cap** (`max_attempts`)
-   **A per-process “retry percent” cap** (budget)
-   **De-synchronization** (full jitter)

### Step 3: requeue with backpressure

A typical controller pattern is:

-   reconcile key
-   if transient failure, requeue key after delay (rate limited)
-   otherwise, forget and move on

Kubernetes’s default controller rate limiter explicitly includes both global and per-item controls. ([pkg.go.dev][4])
You can replicate that design in your own controller: global tokens + per-key exponential backoff.

Even without fully reproducing K8s’s implementation, you can get most of the benefit by:

-   limiting worker count,
-   coalescing keys,
-   and applying jittered backoff before requeue.

### Section summary

-   Combine: retry budget (admission) + jitter (schedule) + queue/worker caps (backpressure).
-   Keep retries bounded and idempotent-aware. ([Google Cloud Documentation][3])

---

## Observability: you can’t tune what you can’t see

The most common retry failure I see in real systems isn’t “wrong algorithm.”

It’s: **no one knows it’s happening** until the control plane is on fire.

At minimum, export:

-   `retries_total{reason=...}`
-   `retry_budget_balance` (or `% remaining`)
-   `retry_budget_exhausted_total`
-   `queue_depth` and `queue_age_seconds` (time-in-queue)
-   `inflight_requests` / `worker_utilization`
-   `rate_limiter_wait_seconds` (how much time you spend waiting to send)

Then add logs for the “interesting” transitions:

-   first failure for a key,
-   budget exhaustion,
-   backoff values growing,
-   repeated failure for same key.

Also watch for **layered retries**: app retries + client library retries + proxy retries = multiplicative explosion. Google’s retry guidance explicitly calls out layering retries as an anti-pattern because it can multiply attempts and increase load/latency. ([Google Cloud Documentation][3])

### Section summary

-   Measure budget usage, retry rates, queue depth/age, and in-flight requests.
-   Avoid multiplicative retries by understanding all retry layers. ([Google Cloud Documentation][3])

---

## Key takeaways

1. **Backoff isn’t enough.** Exponential backoff without jitter still creates retry clusters under correlated failures. ([Amazon Web Services, Inc.][1])
2. **Jitter is the anti-synchronization tool.** Full jitter is a strong default; decorrelated jitter is a solid alternative. ([Amazon Web Services, Inc.][1])
3. **Retry budgets are the fuse.** Limit retries to a percentage of normal traffic; when normal traffic stops, retries naturally shut off.
4. **Backpressure belongs in the controller loop.** Use coalescing queues, worker caps, and rate limiting to protect the backend. ([pkg.go.dev][4])
5. **Idempotency is non-negotiable.** Don’t blindly retry non-idempotent operations; make operations safe to repeat or avoid automatic retries. ([Google Cloud Documentation][3])
6. **Instrument everything.** Budget exhaustion and queue growth are early warning signs of cascading failure.

---

## Further reading

If you want to go deeper (and steal good ideas shamelessly):

-   AWS Architecture Blog: analysis of exponential backoff and different jitter strategies (full/equal/decorrelated). ([Amazon Web Services, Inc.][1])
-   Finagle `RetryBudget`: a concrete, battle-tested API for retry budgets (deposit/withdraw, percent-based budgeting, TTL windows).
-   Google SRE Book (Handling Overload): client-side throttling and retry budgeting ideas (including per-request caps and per-client retry ratios). ([Google SRE][2])
-   Kubernetes `workqueue`: “fair” + “stingy” queue semantics and controller rate limiting design. ([pkg.go.dev][4])
-   Google Cloud retry strategy guidance: practical retry anti-patterns and recommendations (backoff + jitter, idempotency, avoid layered retries). ([Google Cloud Documentation][3])

[1]: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/ "Exponential Backoff And Jitter | AWS Architecture Blog"
[2]: https://sre.google/sre-book/handling-overload/ "Google SRE: Load Balancing with Client Side Throttling"
[3]: https://docs.cloud.google.com/storage/docs/retry-strategy "Retry strategy  |  Cloud Storage  |  Google Cloud Documentation"
[4]: https://pkg.go.dev/k8s.io/client-go/util/workqueue "workqueue package - k8s.io/client-go/util/workqueue - Go Packages"
