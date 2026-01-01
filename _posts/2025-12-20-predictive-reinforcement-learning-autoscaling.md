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
    overlay_image: /assets/images/predictive-reinforcement-learning-autoscaling/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/predictive-reinforcement-learning-autoscaling/banner.png
title: "Predictive Scaling 2.0: Using Reinforcement Learning to Optimize Kubernetes Autoscaling Policies"
tags:
    - predictive
    - autoscaling policis
    - reinforcement learning
---

It’s 02:37. Your phone vibrates like it’s trying to tunnel through the nightstand.

**“p95 latency > SLO for 8 minutes”**

You open Grafana. CPU looks fine-ish. Pods are scaling… eventually. But the backlog (queue depth) climbed faster than your HPA could react, and now your users are doing the digital equivalent of tapping their foot at the counter.

If you’ve run Kubernetes in production, you’ve probably had some version of this moment: **the autoscaler is “working,” but not fast enough, not consistently enough, or not for the metric you actually care about.**

This post is about a next step beyond “set target CPU to 60% and call it a day”:

-   treat autoscaling as a **policy** (not a threshold),
-   measure outcomes in **latency and queue depth** (not just resource utilization),
-   and let an **RL agent learn how aggressive scaling should be** under different workload patterns.

We’ll build a prototype RL setup that **controls scaling thresholds** (e.g., the target value in an HPA that tracks “queue depth per pod”), then discuss how to wire it into Kubernetes _safely_.

---

## The uncomfortable truth about HPA: it’s reactive control with a speed limit

Kubernetes HPA is, at heart, a feedback controller.

It observes a metric and computes a desired replica count using a ratio-based rule that (conceptually) looks like:

```text
desiredReplicas = ceil(currentReplicas * currentMetricValue / desiredMetricValue)
```

So if your metric is “queue depth per pod”:

-   current: 40 messages per pod
-   desired target: 20 messages per pod
-   replicas: 10

Then:

-   desired replicas ≈ ceil(10 \* 40 / 20) = 20

That’s a perfectly reasonable control law—**if**:

-   metrics are timely,
-   the system responds quickly,
-   the workload isn’t bursty in a way that outruns your control loop,
-   and the target value you chose is “right” across all regimes.

In real systems, those assumptions crack:

### Where the lag comes from

Even when everything is configured well, scaling has unavoidable delays:

-   metrics scrape intervals + aggregation windows
-   HPA sync period
-   scheduling latency
-   image pulls and container startup time
-   warm-up effects (JIT, caches, connection pools)
-   load balancer propagation (sometimes)

So HPA is often playing catch-up. You can tune it, sure—but you’re still tuning a reactive loop.

### The target value is a policy decision disguised as a constant

If you set:

-   “target CPU = 60%”
    or
-   “target queue depth per pod = 20”

…you’re encoding an _opinion_:

-   How much headroom do you want?
-   How much latency risk is acceptable?
-   How much cost are you willing to pay to prevent a backlog spike?
-   How bursty is “normal,” and how bursty is “panic”?

Those aren’t static truths. They change with:

-   time of day
-   deployment versions (latency profile changes!)
-   downstream dependencies
-   traffic mix (read-heavy vs write-heavy)
-   queue service behavior

So the interesting question becomes:

> What if the autoscaler _learned_ how aggressive it should be, instead of you guessing one number forever?

---

## “Predictive scaling” isn’t just forecasting — it’s choosing actions under uncertainty

When people say “predictive autoscaling,” they often mean:

-   forecast traffic (ARIMA, Prophet, LSTM, etc.)
-   scale ahead of demand

That’s useful, but it’s still incomplete: forecasting tells you what might happen; it doesn’t tell you what you should _do_ given tradeoffs.

Autoscaling is inherently a **decision problem**:

-   Scale up early → lower latency risk, higher cost
-   Scale late → higher latency risk, lower cost
-   Scale down aggressively → lower cost, risk thrash and cold-start pain
-   Scale down slowly → stable, but you pay longer

This is where reinforcement learning fits surprisingly well.

---

## Reinforcement learning, in autoscaling terms

RL sounds fancy, but the core idea is simple:

-   the system is in a **state**
-   you take an **action**
-   you observe a **reward**
-   you learn a policy that maximizes expected reward over time

Let’s map that to autoscaling.

### State (what the agent observes)

A practical state vector might include:

-   current replicas
-   queue depth (total)
-   queue depth per pod
-   request rate (RPS) or arrival rate
-   p50 / p95 latency
-   CPU and memory (optional)
-   recent trend features (deltas, rolling averages)

### Action (what the agent controls)

Since you asked specifically about _controlling scaling thresholds_, a clean action is:

-   choose a new target value for an HPA metric

Example: we scale on `queue_depth_per_pod`, but the agent chooses the target:

-   conservative: target = 30 → scale less aggressively
-   aggressive: target = 10 → scale more aggressively

This is a neat trick because it lets you **reuse HPA as the actuator**, and RL only tweaks “how jumpy” it is.

### Reward (what the agent is optimizing)

A typical reward balances SLO and cost:

-   big penalty for latency above SLO
-   smaller penalty for backlog growth
-   cost penalty per replica
-   penalty for scaling too frequently (thrash)

A simple shaped reward might look like:

```text
reward =
  - 5.0 * max(0, p95_latency - slo_ms) / slo_ms
  - 1.0 * queue_depth_per_pod / target_backlog
  - 0.05 * replicas
  - 0.2 * |replicas - prev_replicas|
```

You can tune the weights to reflect business reality: “latency is sacred” vs “cost is sacred.”

---

## A toy simulator: queueing + pods + scaling delays

Before you aim RL at production, you want an environment you can:

-   run fast,
-   reset,
-   replay,
-   and learn in without burning real money.

We’ll build a tiny discrete-time simulator:

-   requests arrive each tick (bursty pattern)
-   pods process requests at a fixed service rate per pod
-   queue accumulates
-   latency is estimated from queue length (roughly: queueing delay)

This is not a perfect model. That’s fine—the goal is to prototype the learning loop and control strategy.

### Step 1: the environment

```python
import math
import random
from dataclasses import dataclass

@dataclass
class SimState:
    t: int
    replicas: int
    queue: float
    arrival_rate: float   # req/s
    p95_ms: float

class QueueSimEnv:
    """
    Toy autoscaling environment.

    - Each tick is 1 second.
    - Arrivals are sampled around arrival_rate (bursty).
    - Each pod can process svc_rate req/s.
    - p95 latency is approximated from queue length and service capacity.

    This is deliberately simple: we want a controllable sandbox, not a thesis.
    """
    def __init__(self, svc_rate_per_pod=30.0, slo_ms=200.0,
                 min_rep=2, max_rep=50, scale_delay=5):
        self.svc_rate_per_pod = svc_rate_per_pod
        self.slo_ms = slo_ms
        self.min_rep = min_rep
        self.max_rep = max_rep

        # Scaling isn't instant: new replicas become effective after N seconds.
        self.scale_delay = scale_delay
        self.pending_replica_changes = []  # list of (t_effective, new_replica_count)

        self.reset()

    def reset(self):
        self.t = 0
        self.replicas = self.min_rep
        self.queue = 0.0
        self.arrival_rate = 20.0
        self.p95_ms = 50.0
        self.pending_replica_changes.clear()
        return self._obs()

    def _obs(self):
        queue_per_pod = self.queue / max(1, self.replicas)
        return {
            "t": self.t,
            "replicas": self.replicas,
            "queue": self.queue,
            "queue_per_pod": queue_per_pod,
            "arrival_rate": self.arrival_rate,
            "p95_ms": self.p95_ms,
        }

    def _update_workload(self):
        """
        Create bursts: mostly stable, occasionally spikes.
        """
        base = 20.0 + 10.0 * math.sin(self.t / 30.0)
        spike = 0.0
        if random.random() < 0.02:  # ~2% chance each second
            spike = random.uniform(50.0, 120.0)
        self.arrival_rate = max(1.0, base + spike)

    def _apply_pending_scaling(self):
        """
        If a scaling decision was made scale_delay seconds ago, it takes effect now.
        """
        for (t_eff, rep) in list(self.pending_replica_changes):
            if t_eff <= self.t:
                self.replicas = max(self.min_rep, min(self.max_rep, rep))
                self.pending_replica_changes.remove((t_eff, rep))

    def step(self, desired_replicas):
        """
        Actuator: set desired replica count (as if HPA computed it).
        We delay its effect to mimic real scheduling + startup.
        """
        self._apply_pending_scaling()

        # Schedule change
        desired_replicas = int(max(self.min_rep, min(self.max_rep, desired_replicas)))
        self.pending_replica_changes.append((self.t + self.scale_delay, desired_replicas))

        # Update workload + arrivals
        self._update_workload()
        arrivals = max(0.0, random.gauss(self.arrival_rate, self.arrival_rate * 0.1))

        # Service capacity
        capacity = self.replicas * self.svc_rate_per_pod
        served = min(self.queue + arrivals, capacity)

        # Update queue
        self.queue = max(0.0, self.queue + arrivals - served)

        # Latency proxy: queueing delay ~ queue / capacity seconds
        queue_delay_s = (self.queue / max(1.0, capacity))
        self.p95_ms = 50.0 + 1000.0 * queue_delay_s * 1.5  # p95-ish multiplier

        self.t += 1
        done = (self.t >= 600)  # 10 minute episode
        return self._obs(), done
```

**Summary so far:** We’ve built a simple world where:

-   scaling has delays,
-   bursts happen,
-   queue depth impacts latency.

Now we need a controller.

---

## Use HPA math as the actuator, and let RL choose the target

Instead of having RL directly pick replica counts (which can be unstable fast), we’ll do:

1. RL chooses a **target queue depth per pod** (a threshold/policy knob).
2. The “HPA formula” computes desired replicas based on that target.

This mirrors what you’d do in Kubernetes: scale on a queue-depth metric, but dynamically adjust the target.

### The HPA-style replica computation

```python
def hpa_desired_replicas(current_replicas, current_metric, target_metric,
                        min_rep=2, max_rep=50):
    """
    Conceptual HPA formula for a single metric:
      desired = ceil(currentReplicas * currentMetric / targetMetric)

    Here, metric = queue_depth_per_pod.
    """
    target_metric = max(1e-6, target_metric)
    desired = math.ceil(current_replicas * (current_metric / target_metric))
    return int(max(min_rep, min(max_rep, desired)))
```

So now the RL agent’s action is: choose `target_metric` from a small set (discrete actions are easier to prototype).

Example action set:

```python
TARGETS = [5, 10, 15, 20, 30, 40]  # desired queue depth per pod
```

Low target = aggressive scaling. High target = chill scaling.

---

## Training a small Q-learning agent (prototype-grade, but illustrative)

For a first pass, we’ll:

-   discretize observations into bins,
-   run tabular Q-learning,
-   and learn which target to pick under which conditions.

This is not how you’d build a production-grade policy (you’d likely use a function approximator), but it’s perfect for understanding the mechanics.

### Discretize state

```python
def bucketize(x, bins):
    for i, b in enumerate(bins):
        if x < b:
            return i
    return len(bins)

QUEUE_BINS = [0, 20, 50, 100, 200, 400]
LAT_BINS   = [100, 150, 200, 300, 500, 800]
RATE_BINS  = [20, 40, 60, 80, 120]

def encode_state(obs):
    return (
        bucketize(obs["queue_per_pod"], QUEUE_BINS),
        bucketize(obs["p95_ms"], LAT_BINS),
        bucketize(obs["arrival_rate"], RATE_BINS),
        min(10, obs["replicas"])  # clamp replicas bucket
    )
```

### Reward shaping

```python
def compute_reward(obs, slo_ms=200.0, cost_per_rep=0.02, thrash_pen=0.1, prev_rep=None):
    slo_violation = max(0.0, obs["p95_ms"] - slo_ms) / slo_ms
    backlog_pen = obs["queue_per_pod"] / 50.0  # scale factor
    cost = cost_per_rep * obs["replicas"]

    thrash = 0.0
    if prev_rep is not None:
        thrash = thrash_pen * abs(obs["replicas"] - prev_rep)

    # Negative penalties: higher is better
    return -(5.0 * slo_violation + 1.0 * backlog_pen + cost + thrash)
```

### Q-learning loop

```python
from collections import defaultdict

def train_q(env, episodes=200, alpha=0.1, gamma=0.95,
            eps_start=1.0, eps_end=0.05):
    Q = defaultdict(lambda: [0.0 for _ in TARGETS])

    for ep in range(episodes):
        obs = env.reset()
        s = encode_state(obs)
        eps = eps_end + (eps_start - eps_end) * math.exp(-ep / (episodes / 5))

        prev_rep = obs["replicas"]

        while True:
            # epsilon-greedy action selection
            if random.random() < eps:
                a = random.randrange(len(TARGETS))
            else:
                a = max(range(len(TARGETS)), key=lambda i: Q[s][i])

            target = TARGETS[a]
            desired = hpa_desired_replicas(
                current_replicas=obs["replicas"],
                current_metric=obs["queue_per_pod"],
                target_metric=target,
                min_rep=env.min_rep,
                max_rep=env.max_rep
            )

            next_obs, done = env.step(desired)
            r = compute_reward(next_obs, slo_ms=env.slo_ms, prev_rep=prev_rep)

            s2 = encode_state(next_obs)

            # Q update
            best_next = max(Q[s2])
            Q[s][a] = (1 - alpha) * Q[s][a] + alpha * (r + gamma * best_next)

            obs = next_obs
            prev_rep = obs["replicas"]
            s = s2

            if done:
                break

    return Q
```

**What you should expect from this prototype:** after training, the agent learns patterns like:

-   “If latency is high and queue per pod is climbing → choose a low target (aggressive).”
-   “If the system is calm → choose a higher target (save cost).”
-   “If arrival rate is rising but latency is still OK → preemptively lower target.”

That “preemptive” behavior is the interesting bit: **it’s not true prediction**, but it’s learned _anticipation_ based on observed trends and delayed system response.

---

## Wiring it into Kubernetes: RL as a “policy knob” controller

Let’s talk about the real cluster.

The safest integration pattern is:

1. Keep a normal HPA that scales based on an external metric (queue depth per pod).
2. Run an “RL policy controller” that periodically patches the HPA target value (within guardrails).
3. Add hard limits and fallbacks.

### HPA manifest (scaling on queue depth per pod)

This assumes you expose `queue_depth` and/or `queue_depth_per_pod` via the External Metrics API (often via Prometheus Adapter), or you use a scaler framework like KEDA. The details differ, but the idea is consistent.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
    name: worker-hpa
spec:
    scaleTargetRef:
        apiVersion: apps/v1
        kind: Deployment
        name: queue-worker
    minReplicas: 2
    maxReplicas: 50

    metrics:
        - type: External
          external:
              metric:
                  name: queue_depth_per_pod
              target:
                  type: Value
                  value: "20" # <-- RL will patch this within a safe range

    behavior:
        scaleUp:
            stabilizationWindowSeconds: 0
            policies:
                - type: Percent
                  value: 100
                  periodSeconds: 60
        scaleDown:
            stabilizationWindowSeconds: 300
            policies:
                - type: Percent
                  value: 30
                  periodSeconds: 60
```

Notice we’re **not** letting RL scale replicas directly. Kubernetes still owns:

-   replica min/max
-   scale velocity constraints
-   stabilization windows

RL only adjusts how “tight” the target is.

That’s a good division of labor.

---

## A minimal “RL threshold controller” loop (patching HPA target)

Below is a sketch of a controller-style loop:

-   reads metrics (latency/queue/rate) from your metrics system
-   chooses a target (from `TARGETS`)
-   patches the HPA target value
-   rate-limits changes
-   includes a fallback mode

```python
import time
from kubernetes import client, config

SAFE_TARGET_MIN = 5
SAFE_TARGET_MAX = 40
PATCH_INTERVAL_S = 30
MAX_TARGET_STEP = 10  # don't swing too wildly

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def patch_hpa_target(namespace, hpa_name, new_target_value):
    api = client.AutoscalingV2Api()

    patch = {
        "spec": {
            "metrics": [{
                "type": "External",
                "external": {
                    "metric": {"name": "queue_depth_per_pod"},
                    "target": {"type": "Value", "value": str(int(new_target_value))}
                }
            }]
        }
    }

    api.patch_namespaced_horizontal_pod_autoscaler(
        name=hpa_name,
        namespace=namespace,
        body=patch
    )

def choose_target_from_Q(Q, obs):
    s = encode_state(obs)
    a = max(range(len(TARGETS)), key=lambda i: Q[s][i])
    return TARGETS[a]

def controller_main(Q, namespace="default", hpa_name="worker-hpa"):
    config.load_incluster_config()  # or load_kube_config() for local testing

    current_target = 20  # start from something sane
    last_patch = 0

    while True:
        # 1) Gather metrics (pseudo-code; replace with your actual query)
        obs = {
            "replicas": get_current_replicas("queue-worker"),  # from K8s API
            "queue_per_pod": get_queue_depth() / max(1, get_current_replicas("queue-worker")),
            "arrival_rate": get_rps(),
            "p95_ms": get_p95_latency_ms(),
            "queue": get_queue_depth(),
            "t": int(time.time()),
        }

        # 2) Choose new target
        proposed = choose_target_from_Q(Q, obs)

        # 3) Safety clamps + smoothing
        proposed = clamp(proposed, SAFE_TARGET_MIN, SAFE_TARGET_MAX)
        delta = proposed - current_target
        delta = clamp(delta, -MAX_TARGET_STEP, MAX_TARGET_STEP)
        proposed = current_target + delta

        # 4) Patch periodically (avoid flapping the HPA spec)
        now = time.time()
        if now - last_patch > PATCH_INTERVAL_S and proposed != current_target:
            patch_hpa_target(namespace, hpa_name, proposed)
            current_target = proposed
            last_patch = now

        time.sleep(5)
```

### Why patching the HPA spec isn’t insane (if you’re careful)

You are essentially turning the HPA into a _two-layer controller_:

-   inner loop (HPA): computes replicas from metric vs target
-   outer loop (RL): chooses target to optimize end-to-end outcome

This architecture is common in control systems: a fast stabilizing loop inside, and a slower optimizing loop outside.

---

## Production reality: the “don’t page yourself” checklist

This is the part where we admit RL can absolutely make things worse if you treat it like magic.

Here are the guardrails I’d put in place before anything touches production traffic.

### 1) Start as “advisory mode”

Instead of patching the HPA immediately:

-   run the agent
-   log proposed targets
-   compare against a static target baseline
-   compute “counterfactual” outcomes where possible (or at least analyze correlations)

This buys you confidence and data.

### 2) Constrain the action space

Keep targets within a tight, tested band. Don’t allow:

-   “target = 1” (panic scaling forever)
-   “target = 10,000” (never scale, enjoy your outage)

### 3) Rate-limit policy changes

Even if the agent updates every 5 seconds, only patch every 30–60 seconds (or longer). Let the system respond.

### 4) Add a “latency circuit breaker”

If latency exceeds SLO by a lot, temporarily override RL with a known safe aggressive policy, e.g.:

-   set target to minimum
-   or temporarily raise maxReplicas (if your cluster can handle it)

Then let RL resume after the incident clears.

### 5) Train offline, then fine-tune carefully

Production learning (“online RL”) is alluring but risky:

-   exploration means trying worse actions on purpose
-   the environment is non-stationary (deploys, outages, downstream slowness)

A practical approach:

-   train offline in simulation and/or replay (logged metrics)
-   deploy as a conservative policy
-   update models on a schedule with human review

### 6) Know what RL can’t fix

If your bottleneck is:

-   a database connection pool cap
-   a downstream rate limit
-   lock contention
-   a single-threaded consumer
    …scaling pods won’t help. RL will just learn “more replicas doesn’t buy reward,” which is educational, but not a solution.

---

## Where this gets really interesting (and “Predictive Scaling 2.0” earns the name)

Once you’re comfortable with the threshold-control loop, you can expand the agent’s role:

-   **multi-objective policies**: different weights at different times (business hours vs nights)
-   **SLO-aware scaling**: directly optimize error budget burn rate
-   **contextual scaling**: include deployment version, feature flags, region, dependency health
-   **multiple actuators**: adjust concurrency limits, queue batching, worker thread pools (not just replicas)

At that point, “autoscaling” starts to look like **runtime optimization** more than “add pods when CPU is high.”

---

## Key takeaways

-   **HPA is a solid inner loop**, but the target values you pick are often _policy guesses_.
-   **Reinforcement learning fits autoscaling** because autoscaling is fundamentally a sequential decision problem with tradeoffs.
-   A safe and practical first integration is:
    **RL chooses the target threshold**, HPA chooses replicas.
-   You can prototype RL effectively in a toy simulator to validate:

    -   reward shaping
    -   action constraints
    -   stability under delay and bursts

-   Production success is less about fancy models and more about:

    -   guardrails
    -   observability
    -   slow rollout
    -   safe fallback behavior

---

## Further reading and next steps

If you want to go deeper after this prototype:

-   Kubernetes docs on **Horizontal Pod Autoscaling (autoscaling/v2)**, especially scaling behavior and stabilization windows
-   Concepts from classic control:

    -   proportional control and hysteresis
    -   PID controllers and why they’re both loved and feared

-   Queueing fundamentals:

    -   **Little’s Law** and how queue length relates to delay

-   Reinforcement learning fundamentals:

    -   Sutton & Barto, _Reinforcement Learning: An Introduction_

-   Practical RL tooling (if you go beyond tabular methods):

    -   policy gradient / actor-critic approaches (often used when state is continuous)
    -   offline RL and replay-based training
