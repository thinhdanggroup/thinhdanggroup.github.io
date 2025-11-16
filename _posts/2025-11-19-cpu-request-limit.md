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
    overlay_image: /assets/images/cpu-request-limit/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/cpu-request-limit/banner.png
title: "Demystifying CPU Requests and Limits in Kubernetes: How the Scheduler Really Works"
tags:
    - kubernetes
    - cfs quotas
---

Most of us learn “set CPU requests and limits” as a cargo-cult rule. Then, sooner or later, a service starts stuttering under load and someone declares: _“Never set CPU limits!”_ Another teammate counters: _“No, limits protect us from noisy neighbors!”_ And the Slack thread turns into a philosophical debate about fairness, spikes, and what the scheduler **actually** does.

This post aims to end that argument with a clear mental model, a few concrete experiments you can run yourself, and a practical playbook. We’ll peel back the layers—Kubernetes scheduler, kubelet, Linux cgroups, and the Completely Fair Scheduler (CFS)—to see how requests and limits translate into CPU **shares** and **quotas**, how pods are placed, and why throttling happens.

By the end, you’ll know exactly what knobs control **placement**, **fairness under contention**, and **hard ceilings**, and how to choose sane defaults for your workloads.

---

## Table of Contents

1. The Two Halves: Placement vs. Enforcement
2. CPU Units 101: Cores, millicores, and what “1 CPU” means
3. CFS Shares: Proportional fairness when everyone wants the CPU
4. CFS Quotas: Limits, periods, and throttling (a ceiling with teeth)
5. Kubernetes QoS and CPU Manager: From fair sharing to exclusive cores
6. Common Configurations (and what actually happens)
7. A Mini-Lab You Can Run: See shares and throttling for yourself
8. Tuning Playbook: Low-latency, batch, and everything in between
9. Edge Cases: Multi-container pods, hyperthreading, topology
10. Metrics to Watch
11. Summary & Further Reading

---

## 1) The Two Halves: Placement vs. Enforcement

Kubernetes divides the world neatly:

-   **Scheduler (placement)**: Decides _where_ a Pod goes. For CPU, it only cares about **requests**. It bin-packs requested CPUs onto nodes that have allocatable room. **Limits are irrelevant to scheduling.**

-   **Kubelet + Container Runtime (enforcement)**: Once the Pod is on a node, kubelet configures Linux **cgroups** for each container. Two knobs matter:

    -   **cpu.shares (or cpu.weight on cgroup v2)** — controls **relative** CPU share when the CPU is congested. Derived from **requests**.
    -   **CFS quota/period (cpu.cfs_quota_us / cpu.cfs_period_us or cpu.max on cgroup v2)** — enforces a **hard ceiling**. Derived from **limits**.

Think of the scheduler as the maître d’ who promises you _at least_ a table size (the request), while kubelet sets table etiquette: how fast you can eat when the restaurant is crowded (shares) and whether the waiter will stop serving you after a fixed number of bites per minute (quota).

**Key truth:**

-   **Requests → placement + shares** (floor-ish under contention)
-   **Limits → quota → throttling** (hard ceiling)

---

## 2) CPU Units 101: Cores, millicores, and what “1 CPU” means

Kubernetes standardizes CPU as:

-   `1` CPU = one physical core or one virtual CPU (vCPU)
-   `1000m` = `1` CPU
-   `250m` = 0.25 CPU

Nodes advertise capacity and allocatable CPU in the same units. The scheduler ensures the sum of **requests** of all scheduled Pods on a node doesn’t exceed allocatable CPU (ignoring overcommit configurations like system-reserved/kube-reserved for brevity).

---

## 3) CFS Shares: Proportional fairness when everyone wants the CPU

Linux’s Completely Fair Scheduler (CFS) implements time-sharing. When CPU is **not** saturated, a container can use as much idle CPU as it can grab (subject to limits). When CPU **is** saturated, CFS uses **shares/weights** to divide time proportionally.

Kubernetes sets **CPU shares proportional to the container’s CPU request**. If two containers contend:

-   Container A: `requests.cpu: 1000m`
-   Container B: `requests.cpu: 500m`

Then A will get roughly **2×** the CPU time of B while CPU is saturated. If exactly one core is fully busy, expect ~66% vs ~33% allocations on average.

This is a **relative** guarantee: if nobody else is contending, a container can exceed its request freely (up to node capacity, or limit if you set one).

> Important nuance: If you omit CPU requests, the runtime will still assign default shares. However, in Kubernetes, if you specify a **limit** but omit a **request**, Kubernetes defaults the **request to the limit** for that container, which affects both scheduling and shares. If you specify **neither**, the Pod falls into the **BestEffort** QoS class and receives the lowest scheduling priority and the least favorable CPU share when resources are tight.

---

## 4) CFS Quotas: Limits, periods, and throttling (a ceiling with teeth)

**CPU limits** become **CFS quotas**. Conceptually:

-   **Period** (typically 100ms): the window CFS looks at.
-   **Quota**: how much CPU time you can consume per period.

If you set `limits.cpu: 500m`, the runtime sets quota ≈ **50ms per 100ms period**. If your container wants to use more than that, the kernel **throttles** it until the next period begins.

This matters for **latency**:

-   A tight quota can cause bursts of progress followed by forced idle time, which shows up as tail latency and throughput cliffs under load.
-   If you care about p99 latency, unintentional throttling often looks exactly like a mysterious stall every ~100ms.

**No CPU limit** means **no CFS quota**. The container can burst above its request as long as the node has headroom and neighbors aren’t outcompeting it via shares.

---

## 5) Kubernetes QoS and CPU Manager: From fair sharing to exclusive cores

Kubernetes assigns each Pod a **QoS class** based on how you set requests/limits for **every** container:

-   **Guaranteed**: For both CPU and memory, **requests = limits** in every container.
-   **Burstable**: At least one request set, but not all requests equal limits.
-   **BestEffort**: No requests and no limits.

QoS impacts eviction and, indirectly, CPU behavior (via how requests map to shares). For CPU-sensitive workloads, there’s another tool:

**CPU Manager (kubelet)**
In **static** policy, if a container in a **Guaranteed** Pod requests an **integer number of CPUs** where **request = limit**, kubelet can assign **exclusive CPUs** via cpusets. This gives you strong isolation: no one else is scheduled onto those logical CPUs, and you avoid share-based contention on those cores. It’s a staple for low-latency services and high-performance caches.

---

## 6) Common Configurations (and what actually happens)

### A) Requests < Limits (Burstable “bursty” services)

-   **Scheduler** reserves only the **request**. Your Pod can be co-located with many others, because you’ve told the scheduler you only _need_ that much.
-   **At runtime**, you get **shares** proportional to the request. When the node is busy, you’re guaranteed only that proportion.
-   You **can** burst above the request up to the **limit** (if set). If the limit is present, quota/throttling kicks in; if not, you can burst up to node capacity.

**When it shines:** Spiky workloads that are fine with “best effort” bursting and degrade gracefully under contention.
**Risk:** If the node is often busy, you may see lower and more-variable CPU than your average need—because you only reserved a small slice.

---

### B) Requests = Limits (predictable capacity; may unlock exclusive CPUs)

-   **Scheduler** reserves the full amount.
-   **Runtime** sets shares to that amount and enforces a matching quota.
-   If the request/limit is a whole number of CPUs and CPU Manager static policy is on, you may get **exclusive CPUs**, which is the gold standard for predictability.

**When it shines:** Latency-sensitive services that need tight SLOs and minimal variance.

---

### C) Limits without Requests

-   In Kubernetes, if you set a **limit** but omit a **request**, Kubernetes defaults the **request to the limit**.
-   Net effect: behaves the same as “Requests = Limits.”

---

### D) Requests without Limits (my personal default for web services)

-   **Scheduler** reserves your request; you get proportional **shares** under contention.
-   **No quota** → **no throttling**. You can use spare CPU to finish work faster, which can reduce latency and improve throughput when the node isn’t maxed out.

**When it shines:** Many production services where occasional bursts help burn down backlog or GC, and you don’t want CFS to stop you mid-sprint.
**Risk:** If everyone does this and your cluster is overcommitted, neighbors may observe more interference at peak times (that’s what shares are for).

---

### E) BestEffort (no requests, no limits)

-   **Scheduler** doesn’t reserve CPU for you.
-   You compete with the lowest priority and least favorable shares under contention.
-   Great for background jobs that mustn’t disrupt anything important.

---

## 7) A Mini-Lab You Can Run: See shares and throttling for yourself

Let’s reproduce common scenarios with tiny Deployments. You can run these on a test cluster or a local node.

### 7.1 Two pods with different requests (shares demo)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
    name: cpu-shares-demo-a
spec:
    replicas: 1
    selector: { matchLabels: { app: demo-a } }
    template:
        metadata: { labels: { app: demo-a } }
        spec:
            containers:
                - name: worker
                  image: busybox
                  command: ["sh", "-c", "yes > /dev/null"]
                  resources:
                      requests:
                          cpu: "1000m"
---
apiVersion: apps/v1
kind: Deployment
metadata:
    name: cpu-shares-demo-b
spec:
    replicas: 1
    selector: { matchLabels: { app: demo-b } }
    template:
        metadata: { labels: { app: demo-b } }
        spec:
            containers:
                - name: worker
                  image: busybox
                  command: ["sh", "-c", "yes > /dev/null"]
                  resources:
                      requests:
                          cpu: "500m"
```

If these land on the **same node** and that node has only one spare CPU, expect A to get ~2× the CPU of B when saturated. Use:

```bash
kubectl top pods
# Or for finer detail, top by container:
kubectl top pod cpu-shares-demo-a-xxxxx --containers
kubectl top pod cpu-shares-demo-b-xxxxx --containers
```

You’ll see A ~66% and B ~33% of a CPU on average (plus/minus). If the node has more idle CPU, both will scale up until they hit the node’s headroom.

### 7.2 Add a limit (quota/throttling demo)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
    name: cpu-quota-demo
spec:
    replicas: 1
    selector: { matchLabels: { app: quota } }
    template:
        metadata: { labels: { app: quota } }
        spec:
            containers:
                - name: worker
                  image: busybox
                  command: ["sh", "-c", "yes > /dev/null"]
                  resources:
                      requests:
                          cpu: "500m"
                      limits:
                          cpu: "500m"
```

This sets a quota of roughly **50ms per 100ms**. Under sustained demand, the kernel will periodically **throttle** the container. On many systems you can inspect:

```bash
# Locate the container’s cgroup path (varies by runtime; examples for cgroup v1):
CID=$(docker ps | grep cpu-quota-demo | awk '{print $1}')   # or use crictl ps / containerd tooling
CG=/sys/fs/cgroup/cpu/docker/$CID

cat $CG/cpu.cfs_quota_us
cat $CG/cpu.cfs_period_us
cat $CG/cpu.stat
# cpu.stat contains nr_periods, nr_throttled, throttled_time (ns)
```

Watch `nr_throttled` tick upwards under load. That’s quota enforcement in action.

> Tip: If you set **no CPU limit**, those `cpu.cfs_*` files (or `cpu.max` on cgroup v2) won’t cap you, and throttling counters won’t climb due to quota.

---

## 8) Tuning Playbook: Low-latency, batch, and everything in between

A few recipes that work well in practice:

### Latency-sensitive services (online APIs, RPC handlers)

-   **Prefer requests without CPU limits** to avoid quota-induced stalls.
-   Size **requests** near your **steady-state p95** CPU usage so you get fair treatment during contention.
-   If you need very tight SLOs, consider **Guaranteed** Pods with **integer CPUs** and **CPU Manager (static)** for **exclusive cores**.
-   Watch for GC/just-in-time compiler spikes; burst-friendly configs help smooth them out.

### Throughput-oriented batch/ETL/background jobs

-   Use **low requests** and set **limits** to protect neighbors.
-   Consider **BestEffort** for opportunistic workloads; they’ll back off automatically when the cluster is hot.

### Spiky web services

-   **Requests < Limits** can be fine: you reserve the average and allow some burst.
-   But remember: when the node is busy, you’ll only get your **share** proportional to the **request**, not the **limit**. Don’t expect consistent performance if your request is dramatically below real need.

### Platform guidance

-   Define **LimitRanges** and **ResourceQuotas** to prevent extremes (e.g., unbounded no-limit Pods or zero-request services).
-   Think in terms of **overcommit ratios** per node pool. For example, allow 2–4× logical CPU overcommit via requests if your workloads are typically IO-bound.

---

## 9) Edge Cases: Multi-container pods, hyperthreading, topology

-   **Multi-container Pods**: Requests/limits apply **per container**. The Pod’s effective “weight” is the sum of its containers’ shares. If one sidecar has no request, it may be starved under contention while the main container is fine (or vice versa). Be explicit for critical sidecars (proxies, log forwarders).

-   **Hyperthreading (SMT)**: Kubernetes counts logical CPUs. `1` CPU typically maps to one **hardware thread**, not a full physical core. Two “CPUs” on the same core may interfere at a microarchitectural level. For the most predictable performance, use **exclusive CPUs** (CPU Manager static); it will allocate whole logical CPUs and can be paired with topology-aware placement.

-   **NUMA & Topology Manager**: For very CPU-sensitive/native code, the **Topology Manager** can align CPU sets and device NUMA locality. This is an advanced topic, but worth exploring if you chase microseconds.

---

## 10) Metrics to Watch

If you run Prometheus (directly or via kube-state-metrics/cAdvisor), these are gold:

-   **Throttling**:

    -   `container_cpu_cfs_throttled_seconds_total`
    -   `container_cpu_cfs_throttled_periods_total`

-   **Configuration**:

    -   `container_spec_cpu_quota`
    -   `container_spec_cpu_period`
    -   `container_spec_cpu_shares`
    -   `kube_pod_container_resource_limits{resource="cpu"}`
    -   `kube_pod_container_resource_requests{resource="cpu"}`

-   **Usage**:

    -   `container_cpu_usage_seconds_total`
    -   `node_cpu_seconds_total` (for node saturation)

-   **Autoscaling**:

    -   `kube_horizontalpodautoscaler_*` and your service latency/RPS

Correlate **throttled_seconds_total** spikes with latency tail blowups. If your p99s line up with periodic throttling and you have limits set, you’ve found a smoking gun.

---

## 11) Myths, Busted

-   **“CPU limits guarantee me that much CPU.”**
    No. A **limit is a ceiling**, not a reservation. It just sets the maximum you can use per period. Under limit, you may still get less when the node is busy.

-   **“CPU requests cap my CPU.”**
    No. A **request is not a cap**. It’s: (a) a scheduling reservation, and (b) your **fair share** when the node is saturated. With no limit set, you can burst above it.

-   **“The scheduler uses limits.”**
    The Kubernetes scheduler ignores limits for CPU placement decisions. It only considers **requests**.

-   **“Never set CPU limits.”**
    Limits are valuable for batch/background jobs or to protect neighbors. For latency-sensitive online paths, limits can cause avoidable throttling. Use them intentionally.

---

## 12) Historical Aside: Why CFS behaves the way it does

Linux’s CFS aims for fairness by modeling an “ideal multitasking processor.” Each runnable entity gets a slice proportional to its weight (shares). Quotas were grafted on to enforce tenancy ceilings—useful in multi-tenant systems (like Kubernetes clusters) but easy to misuse. Kubernetes rides on this machinery, translating your YAML into cgroup knobs that CFS knows how to honor.

---

## 13) Practical YAML Patterns

### A. Sensible default for a typical service

```yaml
resources:
    requests:
        cpu: "300m"
        memory: "512Mi"
    # No cpu limit to avoid throttling; do set a memory limit!
```

Memory limits are a separate can of worms (OOM). For CPU, leaving limits unset avoids quota stalls.

### B. Latency-critical with exclusive CPUs (cluster must enable CPU Manager static)

```yaml
resources:
    requests:
        cpu: "2"
        memory: "1Gi"
    limits:
        cpu: "2"
        memory: "1Gi"
# Pod QoS = Guaranteed; with CPU Manager static, expect exclusive cpusets
```

### C. Background job respectful of neighbors

```yaml
resources:
    requests:
        cpu: "50m"
        memory: "256Mi"
    limits:
        cpu: "500m"
        memory: "512Mi"
```

---

## 14) Putting It All Together (Mental Model)

-   **Placement**: Requests tell the scheduler how much CPU to reserve on a node.
-   **Contention**: Requests become **shares**; when CPU is tight, you get a slice proportional to your request.
-   **Ceilings**: Limits become **quotas**; exceed them and the kernel **throttles** you within each period.
-   **Predictability**: Guaranteed Pods with integer CPUs + CPU Manager (static) can get **exclusive CPUs** and sidestep many interference problems.
-   **Bursts**: No CPU limit = no quota, so you can ride idle capacity to reduce latency and finish work faster.

---

## 15) Quick Checklist

-   [ ] For latency-sensitive paths, **avoid CPU limits** unless you have a strong reason.
-   [ ] Size **requests** to realistic steady-state usage; they control both placement and fairness.
-   [ ] Use **Guaranteed + integer CPUs + CPU Manager** for the most predictable performance.
-   [ ] For batch/background, set **low requests** and **reasonable limits**.
-   [ ] Monitor **throttling** metrics and correlate with latency.
-   [ ] Be explicit with sidecars’ resources—don’t starve your proxies/loggers.
-   [ ] Educate teams: **requests ≠ cap**, **limits ≠ reservation**.

---

## Further Reading

-   Kubernetes docs on **Pod QoS classes** and **Resource Management**
-   Kubelet **CPU Manager** and **Topology Manager** guides
-   Linux kernel docs on **CFS**, **cgroups**, and (for cgroup v2) `cpu.max` and `cpu.weight`
-   Brendan Gregg’s posts on Linux performance and scheduler behavior
-   SRE books/chapters on multi-tenant capacity planning and overcommit

---

### TL;DR

-   The **scheduler** uses **requests** to place Pods.
-   **Requests** turn into **shares**: your proportional slice when CPU is scarce.
-   **Limits** turn into **quotas**: a hard ceiling that can **throttle** you every period.
-   Choose **no CPU limit** for low-latency services (or use exclusive CPUs); use **limits** to tame batch jobs.
-   Measure throttling; tune iteratively.

If you internalize that model, decisions about requests and limits become straightforward knobs instead of folklore.
