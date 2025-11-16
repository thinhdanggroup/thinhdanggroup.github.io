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
    overlay_image: /assets/images/self-healing-systems/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/self-healing-systems/banner.png
title: "Self-Healing Systems: When Auto-Scaling Isn’t Enough"
tags:
    - auto-scaling
---

Auto-scaling is like hiring more baristas when the coffee line wraps around the block.
It absolutely helps with _load_ — more pods, more instances, more throughput.

But if the espresso machine is miscalibrated and every shot is bitter?
Hiring more baristas just means you’re serving **more bad coffee, faster**.

That’s what happens when we treat auto-scaling as resilience. It isn’t.
Resilience is about _recovery_, not just _capacity_. It’s what happens when:

-   A node’s memory slowly leaks and the process gets weird before it dies
-   A network partition leaves half your pods believing they’re the “real” leader
-   A deployment ships a subtle bug that corrupts in-memory state but doesn’t quite crash

This post is about **self-healing systems**: systems that don’t just scale, but _observe their own health, detect when something’s off, and take action to recover — automatically_.

We’ll explore how to build that using:

-   Kubernetes health checks as the first line of defense
-   Chaos engineering to prove your system can actually heal
-   Alert-driven rollbacks that treat “bad deploys” as just another failure mode

By the end, you should have a mental template for going from “we scale” to “we recover”.

---

## 1. Auto-Scaling’s Blind Spot

Let’s start with the comforting lie:

> “If traffic spikes or something goes wrong, auto-scaling will protect us.”

Auto-scaling (HPA, cluster autoscaler, etc.) solves **one specific problem**:

> “I have too much work for my current capacity.”

It responds to signals like CPU, memory, custom metrics (requests/sec, queue length), and spins up more replicas. That’s fantastic — _when the service is healthy_.

But it is completely blind to:

-   **Logical corruption**

    -   E.g., a cache gets into a bad state and starts returning wrong data

-   **Partial failures**

    -   A pod can respond 200 OK but be _latently broken_ (wrong feature flag, stuck background workers, etc.)

-   **Resource leaks**

    -   Memory/FD leaks that lead to intermittent weirdness long before OOM

-   **Network splits**

    -   Multiple leaders, “write went through but I never saw the response”, zombie connections

In those cases, auto-scaling may actually _amplify_ the problem:

> “Oh, your unhealthy pods are returning 500s and the load balancer keeps retrying? Let me… create more of those.”

So we need something else.

---

## 2. What Is a Self-Healing System?

A self-healing system treats failures as routine, expected events and includes the logic to _recover_ from them without human intervention.

At a high level, it needs three things:

1. **Sensing** – _Can I tell when something is wrong?_

    - Health checks, metrics, logs, traces

2. **Decision** – _Is this bad enough that I should act? And how?_

    - Policies, thresholds, SLOs, alert rules

3. **Action** – _What can I do to restore a good state?_

    - Restart, reschedule, rollback, failover, degrade gracefully

Kubernetes gives you decent primitives for (3) — restart pods, reschedule them, roll out new versions. But it doesn’t magically know **when** to do that. That’s where we wire in health checks, chaos experiments, and alert-driven automation.

Let’s start with the basics.

---

## 3. Kubernetes Health Checks: Your First Line of Self-Healing

Kubernetes gives you three main types of probes:

-   **Liveness**: “Should this container be killed and restarted?”
-   **Readiness**: “Should this container receive traffic?”
-   **Startup**: “Is this container still starting up, and should we be patient longer than liveness/readiness allow?”

Most teams start with something like this:

```yaml
livenessProbe:
    httpGet:
        path: /healthz
        port: 8080
    initialDelaySeconds: 10
    periodSeconds: 10

readinessProbe:
    httpGet:
        path: /ready
        port: 8080
    initialDelaySeconds: 5
    periodSeconds: 5
```

Looks good, right? Not quite. These probes are only as good as the **checks your app performs** at `/healthz` and `/ready`.

### 3.1 What Should a “Good” Liveness Probe Check?

Liveness should answer: _“Is this process beyond recovery and needs a restart?”_

Bad candidates:

-   Checking a dependency like the database

    -   If the DB is down, killing all pods just creates a flapping storm

-   Checking something that’s often flaky (like a third-party API)

Good candidates:

-   Internal invariants you can’t recover from without a restart:

    -   The main event loop is stuck
    -   Critical background worker crashed and cannot be restarted from inside the process
    -   Some irreversible initialization failed

Here’s a simplistic Go-style example:

```go
var (
	isStuckAtomic int32 // 0 = ok, 1 = stuck
)

// Somewhere in your main processing loop:
func processMessages() {
	for {
		atomic.StoreInt32(&isStuckAtomic, 0)
		msg := <-messageCh

		// If we don't see this store for longer than X,
		// something is wrong with the loop.
		atomic.StoreInt32(&isStuckAtomic, 1)

		handle(msg)

		atomic.StoreInt32(&isStuckAtomic, 0)
	}
}

func livenessHandler(w http.ResponseWriter, r *http.Request) {
	stuck := atomic.LoadInt32(&isStuckAtomic) == 1
	if stuck {
		http.Error(w, "stuck main loop", http.StatusInternalServerError)
		return
	}
	w.WriteHeader(http.StatusOK)
}
```

This is exaggerated, but the idea is: **tie liveness to “am I in a state that only a restart can fix?”**

### 3.2 What Should Readiness Check?

Readiness answers: _“Can I currently serve traffic successfully?”_

Good candidates:

-   Ability to:

    -   Accept connections
    -   Handle a basic end-to-end request
    -   Access critical dependencies (DB, cache) **with timeouts & retries**

-   Feature flags / configuration loaded correctly

Example readiness endpoint (Node.js-style):

```js
app.get("/ready", async (req, res) => {
    try {
        // very short timeout – if DB is slow, fail fast
        const dbOk = await checkDb({ timeoutMs: 50 });
        const cacheOk = await checkCache({ timeoutMs: 20 });

        if (!dbOk || !cacheOk) {
            return res.status(503).json({ status: "not-ready" });
        }

        return res.json({ status: "ready" });
    } catch (err) {
        return res.status(503).json({ status: "error", error: err.message });
    }
});
```

With this in place, if your DB gets flaky, Kubernetes will **stop routing new traffic** to that pod rather than killing it over and over.

### 3.3 Startup Probe to Avoid “Boot Thrash”

Long startup times are a common pitfall: your app takes 90 seconds to start, but liveness gives up after 30 seconds and kills it… repeatedly.

Use a **startupProbe** to give the app more time to boot, without relaxing liveness forever:

```yaml
startupProbe:
    httpGet:
        path: /startup
        port: 8080
    failureThreshold: 30
    periodSeconds: 5
```

Once the startup probe succeeds, Kubernetes begins checking liveness/readiness.

**Section recap:**
Health checks are your first self-healing sensor. But to be useful, they must reflect _real_ failure modes, not just “is the process alive and port open”.

---

## 4. Beyond Probes: Building Feedback Loops

Health checks alone only drive **local** healing: restart this pod, stop sending it traffic. That’s good, but we also need **global** healing:

-   Roll back a bad deployment
-   Reduce pressure on a failing dependency
-   Shift traffic between regions

For that, you need higher-level feedback loops:

1. Kubernetes probes → **restart / reschedule** pods
2. Metrics/alerts → **trigger rollbacks, scale changes, failovers**
3. Chaos experiments → **validate that 1 & 2 actually work**

Let’s walk through these loops using a practical scenario.

---

## 5. Chaos Engineering: Practicing Recovery on Purpose

Chaos engineering sounds dramatic (“let’s break stuff in prod!”), but the core idea is much more modest:

> Proactively introduce controlled failures to verify that your **self-healing mechanisms actually work**.

If you say “we’re resilient to node failures,” you should be able to:

-   Kill a node
-   Watch your health checks, pods, and controllers react
-   Confirm that your SLOs (latency, error rate) stay within bounds

### 5.1 A Simple Chaos Experiment: Kill a Pod

Assume you have a deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
    name: checkout-service
spec:
    replicas: 5
    selector:
        matchLabels:
            app: checkout
    template:
        metadata:
            labels:
                app: checkout
        spec:
            containers:
                - name: checkout
                  image: myorg/checkout:v2
                  ports:
                      - containerPort: 8080
                  livenessProbe: ...
                  readinessProbe: ...
```

Minimal chaos experiment, conceptually:

1. Send steady traffic through your system (load test or prod traffic).

2. Suddenly delete one of the pods:

    ```bash
    kubectl delete pod checkout-service-abc123
    ```

3. Observe:

    - Does Kubernetes create a new pod quickly?
    - Does the readiness probe prevent unready pods from receiving traffic?
    - Do your dashboards show a brief blip or a noticeable error spike?
    - Do any alerts fire? Are they noisy or reasonable?

You can formalize this using chaos tooling like Chaos Mesh, Litmus, or Gremlin, but even **manual** chaos is better than theoretical resilience.

### 5.2 More Interesting Chaos: Network & Resource Faults

Real-world bugs often emerge under more subtle conditions:

-   High latency between service and database
-   Packet loss between two specific services
-   CPU or memory starvation

A simplified chaos experiment manifest (pseudo-YAML) might look like:

```yaml
apiVersion: chaos.example.com/v1
kind: NetworkLatency
metadata:
    name: checkout-to-db-latency
spec:
    duration: 2m
    target:
        fromSelector:
            app: checkout
        toSelector:
            app: db
    latencyMs: 200
```

When this runs:

-   Do your readiness probes mark too-slow pods as not-ready?
-   Does your service degrade gracefully (e.g., partial features disabled)?
-   Do alerts fire before users are seriously affected?

Chaos experiments aren’t about being edgy; they’re about discovering that your “self-healing” path is actually “self-immolation” before your users do.

**Section recap:**
Chaos engineering is the test suite for resilience. If you never intentionally break things, you’re trusting theory over reality.

---

## 6. Alert-Driven Rollbacks: When the Deployment _Is_ the Incident

Some failures aren’t random infrastructure events — they’re self-inflicted via a deployment.

Imagine:

-   You roll out `checkout:v3`.
-   It passes unit tests, integration tests, and even basic smoke tests.
-   Under production traffic, a memory leak appears, or a pricing bug triggers only for a certain country.

Auto-scaling can’t fix “we deployed bad code.”
Health checks might not immediately fail; the process is _alive_ and responding. It’s just wrong.

What you need is:

1. A way to **link runtime behavior to a specific version**
2. A **policy** that says, “If this version degrades key metrics, roll it back.”
3. Automation to carry that out.

### 6.1 Observability: Tagging by Version

First, make sure every metric/log/trace can be broken down by _version_:

-   Pod label: `version: v3`
-   Kubernetes rollout: different ReplicaSets per version
-   Metrics with label `app_version`

Then you can compute error rate, latency, etc. per version:

```promql
rate(http_requests_total{app="checkout", app_version="v3", status=~"5.."}[5m])
/
rate(http_requests_total{app="checkout", app_version="v3"}[5m])
```

Now you can compare v3 vs v2 directly.

### 6.2 Example: SLO-Based Alert for Rollback

Suppose your SLO is:

-   99.5% of `checkout` requests succeed (`2xx` or `3xx`) over 5 minutes.

Prometheus-style alert (simplified):

```yaml
- alert: CheckoutHighErrorRateV3
  expr: |
      (
        rate(http_requests_total{
          app="checkout",
          app_version="v3",
          status=~"5.."
        }[5m])
      /
        rate(http_requests_total{
          app="checkout",
          app_version="v3"
        }[5m])
      ) > 0.01
  for: 10m
  labels:
      severity: critical
  annotations:
      summary: "checkout v3 has high error rate"
      description: "Error rate for v3 exceeds 1% for 10 minutes"
```

This alert is your _decision_ signal:

> “Version v3 is unhealthy relative to our SLO.”

Now we can wire an **action** to it: rollback.

### 6.3 Wiring Rollbacks into Your CD

If you’re using progressive delivery tools (e.g., Argo Rollouts, Flagger, etc.), they already support metric-based rollbacks. But you can also do this in a more DIY way.

Conceptually:

1. Alert fires → goes to Alertmanager (or your alerting system of choice).
2. Webhook/receiver listens for specific alerts (“CheckoutHighErrorRateV3”).
3. Handler calls your CD tool (e.g., Argo CD, GitOps pipeline, or `kubectl`) to revert to previous version.

Pseudo-handler:

```python
def handle_alert(alert):
    labels = alert["labels"]
    if labels.get("alertname") != "CheckoutHighErrorRateV3":
        return

    service = "checkout"
    bad_version = labels.get("app_version", "v3")

    # Log context for auditing
    log.info("Auto-rollback triggered",
             service=service,
             bad_version=bad_version)

    # This is conceptual – your real integration may call Git, ArgoCD, etc.
    rollback_service(service)
```

What matters is:

-   The **decision logic** is repeatable and based on metrics
-   The **rollback** is automatic but auditable
-   Humans can _override_ or _pause_ automation if needed

Self-healing doesn’t mean “no humans allowed”; it means “humans aren’t the first line of defense for predictable failures.”

**Section recap:**
Alert-driven rollbacks treat bad releases as just another failure mode the system can autonomously correct.

---

## 7. Putting It All Together: A Self-Healing Architecture

Let’s sketch how these pieces fit into a concrete flow.

### 7.1 Scenario: Memory Leak in New Release

You deploy `checkout:v4` with a subtle memory leak.

1. **Initial rollout**

    - 10% of traffic goes to v4, 90% still on v3 (canary release).
    - Probes are passing; nothing crashes (yet).

2. **Slow degradation**

    - Over 20–30 minutes, v4’s pods start using more memory.
    - GC runs more, pauses increase; latency creeps up.
    - Error rate on v4 inches higher than v3.

3. **Health checks react (local healing)**

    - Some v4 pods hit resource limits and either:

        - Fail readiness → removed from service
        - Fail liveness → restarted

    - Kubernetes replaces them, but the _new_ pods still run v4, and the leak continues.

4. **Metrics + alerts detect systemic failure (global detection)**

    - SLO-based alert for v4 error rate fires:

        - “Error rate for v4 > 1% for 10m”

    - Latency SLO for v4 might also trigger.

5. **Automation kicks in (global healing)**

    - Alert triggers rollback logic (via progressive delivery or custom webhook).
    - Traffic is shifted back to v3; v4 is scaled down.
    - Error rate returns to normal.

6. **Chaos engineering validates this flow regularly**

    - You have a chaos experiment that simulates memory pressure on canary pods.
    - It verifies that:

        - Probes behave correctly
        - Alerts trigger appropriately
        - Rollback automation performs a safe revert

The result? The incident was maybe a small blip in your monitoring dashboards.
Pager duty didn’t wake anyone at 3 a.m. The system healed itself.

---

## 8. Practical Design Tips (And Pitfalls to Avoid)

Let’s ground this in some practical advice.

### 8.1 Be Intentional About What Each Probe Does

-   **Liveness**: Only use it for unrecoverable, internal broken states. Don’t tie it to external dependencies unless you truly want to restart on every dependency blip.
-   **Readiness**: Be strict here. It’s okay to fail readiness if dependencies are slow; better to shed load than degrade globally.
-   **Startup**: Use it when boot takes a while. Don’t just increase `initialDelaySeconds` on liveness until it’s effectively useless.

### 8.2 Avoid Flapping

Self-healing mechanisms that constantly oscillate are worse than doing nothing.

Common causes:

-   Alert thresholds that trigger on every tiny blip
-   Probes that check unreliable endpoints and randomly fail
-   Rollbacks that trigger too quickly on small sample sizes

Mitigations:

-   Use `for` durations on alerts (`for: 5m`) to require sustained failure
-   Implement **hysteresis** (“rollback if error rate > 1% for 10m; resume rollout only if < 0.2% for 30m”)
-   Rate-limit automated actions (e.g., no more than 1 rollback per X minutes)

### 8.3 Think in Terms of SLOs, Not Just Raw Metrics

Instead of “alert if CPU > 80%”, think:

-   “Does this violate our **latency** or **error rate** SLOs?”
-   “Are user-visible outcomes degraded?”

This keeps automation focused on what actually matters and avoids reacting to harmless spikes.

### 8.4 Test Your “Recovery Paths” as First-Class Features

Treat these as real features:

-   Rollback scripts / pipelines
-   Failover mechanisms
-   Graceful degradation paths (e.g., disable non-critical features under stress)

Ask yourself:

-   Can a newcomer on the team trigger these safely?
-   Do we have docs?
-   Do we periodically _exercise_ these paths?

You don’t really have a self-healing mechanism if it’s only been run once… three years ago… by someone who’s left the company.

---

## 9. Summary and Further Reading

Auto-scaling is powerful, but it’s not resilience. It handles **how much** work you can do, not **how well** you do it when things go sideways.

To build self-healing systems, you need layered feedback loops:

1. **Kubernetes health checks**

    - Liveness: restart truly broken processes
    - Readiness: shield users from unhealthy pods
    - Startup: handle slow boots gracefully

2. **Chaos engineering**

    - Intentionally break pods, nodes, networks, and dependencies
    - Verify that your health checks, metrics, and controllers behave as you think

3. **Alert-driven rollbacks**

    - Tag metrics by version; watch error rates and latency per release
    - Automate rollbacks using SLO-based alerts and your CD pipeline

When done well, your system:

-   Survives random failures without waking anyone
-   Detects bad releases and rolls them back automatically
-   Treats recovery mechanisms as _normal_, not “break glass” emergencies

If you want to go deeper, good next topics to explore are:

-   Progressive delivery (canary, blue-green, traffic shaping)
-   Pattern libraries for graceful degradation
-   Leader election and split-brain handling in distributed systems
-   Implementing circuit breakers and backpressure in your services

In short: don’t stop at “we auto-scale.”
Aim for “we **self-heal**” — and prove it under fire.
