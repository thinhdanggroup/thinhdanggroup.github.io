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
    overlay_image: /assets/images/ebpf-observability/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/ebpf-observability/banner.png
title: "Tracing the Future: Using eBPF for Low-Overhead Observability in Cloud-Native Systems"
tags:
    - eBPF
    - observability
    - tracing
---

Modern production systems are like busy airports: thousands of “flights” (requests) landing and taking off across microservices, queues, and databases. When a storm rolls in—latency spikes, error rates climb—you need air-traffic-controller-level visibility without shutting down the runway to install new cameras.

That’s the promise of eBPF: dynamic, low-overhead observability from inside the kernel and userspace runtimes, without invasive agents or code changes. Tools like Cilium/Hubble and Pixie have turned eBPF from a research curiosity into day-to-day engineering superpowers. In this post, we’ll unpack how eBPF works, why it’s fast, and how to build practical, production-grade telemetry pipelines with it.

We’ll start with the “why,” zoom into the kernel internals, and then build up hands-on examples (from one-liners to CO-RE/libbpf programs). We’ll finish with deployment patterns in Kubernetes and a checklist of pitfalls to avoid.

---

## TL;DR (for the busy SRE)

eBPF lets you attach tiny, verified programs to kernel (and userspace) hooks—like syscalls, TCP events, or function entry/exit—then stream structured data to user space via lock-free maps and ring buffers. It’s safe (thanks to a bytecode verifier), fast (JIT-compiled), and flexible (attach points range from network drivers to language runtimes). In a cluster, you run these as DaemonSets to get cluster-wide visibility with a surprisingly small CPU/latency tax.

---

## 1) Why eBPF? A quick motivation

Traditional observability stacks trade off three painful axes:

-   **Fidelity**: Sampling hides outliers. Head-based tracing misses the weird tail events you actually care about.
-   **Overhead**: SDKs or sidecars add CPU/memory and can perturb the very timing you’re trying to measure.
-   **Coverage**: System-level issues (TCP retransmits, cgroup throttling, kernel scheduler contention) don’t show up in app logs.

eBPF sidesteps these: instrument the operating system itself (and selected userspace libraries) to capture ground truth, with the kernel ensuring safety and the JIT keeping overhead tiny. You can filter early (in the kernel), send only the metrics you need, and correlate with app-level context using process/container metadata.

---

## 2) eBPF in one diagram (with words)

Think of eBPF as a tiny, sandboxed VM inside the kernel:

1. You write a **BPF program** (in C or a high-level tool like bpftrace).
2. The **BPF verifier** checks it for safety: bounded loops, valid memory access, no uninitialized reads, limited stack, etc.
3. The kernel **JIT-compiles** the bytecode to native instructions.
4. The program gets **attached** to a hook (e.g., a kernel tracepoint, kprobe, uprobe, XDP, LSM).
5. The program emits data via **maps** (hashes, arrays, LRU maps, per-CPU maps) or **ring buffers** for streaming.
6. A user-space component reads the data and exports it to your favorite observability backend.

The magic: BPF runs in kernel context but under strict guardrails—more on those in a second.

---

## 3) Where can we attach BPF programs?

-   **Tracepoints**: Stable kernel events (e.g., `sched:sched_switch`, `tcp:tcp_retransmit_skb`). Stable ABI, ideal for production observability.
-   **kprobes/kretprobes**: Dynamic hooks on almost any kernel function entry/return. Super flexible, less stable than tracepoints.
-   **uprobes/uretprobes**: Hooks on userspace functions (e.g., OpenSSL’s `SSL_read`). Great for application-level telemetry without code changes.
-   **USDT (User-Level Statically Defined Tracing)**: Built-in probes in some runtimes/databases (e.g., PostgreSQL, Java, Go) accessed via uprobes.
-   **XDP / TC**: Earliest and later network path hooks for high-performance packet inspection/processing.
-   **Cgroup / LSM**: Per-cgroup hooks and security instrumentation (useful for multitenant observability and policy).

In practice, you’ll mix and match: use tracepoints for portable system metrics, uprobes for app protocols, and XDP/TC for network flows.

---

## 4) Why is eBPF low overhead?

Several design choices make eBPF efficient:

-   **JIT compilation**: After the verifier, BPF bytecode is JIT-compiled to native instructions per CPU architecture. No interpreter overhead on the hot path.
-   **Early filtering**: Apply predicates in the kernel (e.g., “only for cgroup X,” “only for PID namespace Y,” “only TCP state=ESTABLISHED”). Less data copied to user space.
-   **Per-CPU data structures**: Per-CPU maps avoid cacheline contention.
-   **Lock-free ring buffer**: The BPF ring buffer provides low-latency streaming with backpressure semantics.
-   **Tiny, single-purpose programs**: Short execution time budgets keep latency impacts human-invisible for most workloads.

You still pay _something_ (there is no free lunch in systems), but you can keep the budget to microseconds per event with careful design.

---

## 5) “Hello, hooks!” with a one-liner (bpftrace)

Let’s warm up with a bpftrace example that logs files opened by processes in a specific namespace (pretend: your app container). bpftrace compiles to BPF behind the scenes and is great for exploration:

```bash
# Log filenames opened by a process; store pointer at entry, use it at return.
bpftrace -e '
kprobe:__x64_sys_openat
/comm == "myservice"/
{
  @fname[tid] = arg2;   // arg2 is the filename pointer on x86-64
}

kretprobe:__x64_sys_openat
/@fname[tid]/
{
  printf("%s opened %s -> fd=%d\n", comm, str(@fname[tid]), retval);
  delete(@fname[tid]);
}'
```

What’s happening:

-   We hook the syscall entry to capture the filename pointer (arguments are accessible at entry, not at return).
-   On return, we print the file descriptor and resolve the saved pointer to a string.
-   The filter `/comm == "myservice"/` drops everything else in the kernel—no userspace filter needed.

This is already useful for debugging “why does this container read so many config files?” with negligible overhead.

---

## 6) A real metric: TCP connect latency with BCC (Python)

Let’s measure the latency of `connect()` calls per destination, a classic SRE question when services time out on downstreams.

### Kernel program (C, compiled and injected by BCC)

```c
// tcpconnectlat.c - compiled by BCC; simplified for clarity
#include <uapi/linux/ptrace.h>
#include <net/sock.h>
#include <linux/in.h>
#include <linux/in6.h>
#include <linux/bpf.h>
#include <linux/types.h>

struct val_t {
    u64 ts_ns;
    u32 pid;
};

struct event_t {
    u64 delta_ns;
    u32 pid;
    u32 saddr, daddr;
    u16 dport;
    char comm[16];
};

BPF_HASH(start, u64, struct val_t);
BPF_PERF_OUTPUT(events);

int trace_connect_entry(struct pt_regs *ctx, struct sock *sk) {
    u64 tid = bpf_get_current_pid_tgid();
    struct val_t val = {};
    val.ts_ns = bpf_ktime_get_ns();
    val.pid = tid >> 32;
    start.update(&tid, &val);
    return 0;
}

int trace_connect_return(struct pt_regs *ctx) {
    u64 tid = bpf_get_current_pid_tgid();
    struct val_t *valp = start.lookup(&tid);
    if (!valp) return 0;

    u64 delta = bpf_ktime_get_ns() - valp->ts_ns;

    struct event_t evt = {};
    evt.delta_ns = delta;
    evt.pid = valp->pid;

    // Read IPv4 tuple if available (simplified; production handles IPv6 too)
    struct sock *sk = (struct sock *)PT_REGS_PARM1(ctx);
    if (sk) {
        // Offsets are stable when using tracepoints; kprobes need care.
        u16 dport = 0;
        bpf_probe_read_kernel(&dport, sizeof(dport), &sk->__sk_common.skc_dport);
        bpf_probe_read_kernel(&evt.daddr, sizeof(evt.daddr), &sk->__sk_common.skc_daddr);
        evt.dport = __bpf_ntohs(dport);
    }

    bpf_get_current_comm(&evt.comm, sizeof(evt.comm));
    events.perf_submit(ctx, &evt, sizeof(evt));
    start.delete(&tid);
    return 0;
}
```

### User-space harness (Python)

```python
from bcc import BPF
from socket import inet_ntop, AF_INET

prog = r"""
#include "tcpconnectlat.c"
"""

b = BPF(text=prog)
b.attach_kprobe(event="tcp_v4_connect", fn_name="trace_connect_entry")
b.attach_kretprobe(event="tcp_v4_connect", fn_name="trace_connect_return")

def handle(cpu, data, size):
    event = b["events"].event(data)
    print(f"{event.comm.decode()} pid={event.pid} connect "
          f"{inet_ntop(AF_INET, event.daddr.to_bytes(4, 'little'))}:{event.dport} "
          f"latency={event.delta_ns/1e6:.2f} ms")

b["events"].open_perf_buffer(handle)
print("Tracing connect()... Ctrl-C to quit")
while True:
    b.perf_buffer_poll()
```

Notes:

-   We record a timestamp at function entry, compute the delta at return, and emit a compact event struct.
-   In production you’d prefer a **tracepoint** (stable ABI) over a kprobe here, and migrate to the **ring buffer** API for lower overhead and backpressure.
-   This single script often surfaces DNS issues, SYN backlog pressure, or slow downstreams in minutes.

---

## 7) From exploration to production: libbpf + CO-RE

Exploration tools (bpftrace, BCC) are perfect in a shell, but production agents need:

-   **Compile Once, Run Everywhere (CO-RE)**: Thanks to **BTF** (BPF Type Format), you can compile against a virtual `vmlinux.h` and let relocations adjust struct offsets at load time across kernels. No per-kernel compile matrix.
-   **libbpf**: A lightweight C library to load and manage BPF objects, maps, and ring buffers.

### Minimal CO-RE program (kernel side)

```c
// tcp_retransmit.bpf.c - CO-RE, libbpf-style
#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>
#include <bpf/bpf_core_read.h>

struct event {
    __u64 ts_ns;
    __u32 saddr, daddr;
    __u16 sport, dport;
};

struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 1 << 24); // 16 MiB
} rb SEC(".maps");

SEC("tracepoint/tcp/tcp_retransmit_skb")
int on_retransmit(struct trace_event_raw_tcp_event_sk *ctx)
{
    struct event *e = bpf_ringbuf_reserve(&rb, sizeof(*e), 0);
    if (!e) return 0;

    struct sock *sk = (struct sock *)ctx->skaddr;
    __u16 sport = 0, dport = 0;
    __u32 saddr = 0, daddr = 0;

    // CO-RE reads: field offsets handled at load time
    BPF_CORE_READ_INTO(&sport, sk, __sk_common.skc_num);
    BPF_CORE_READ_INTO(&dport, sk, __sk_common.skc_dport);
    BPF_CORE_READ_INTO(&saddr, sk, __sk_common.skc_rcv_saddr);
    BPF_CORE_READ_INTO(&daddr, sk, __sk_common.skc_daddr);

    e->ts_ns = bpf_ktime_get_ns();
    e->sport = sport;
    e->dport = __bpf_ntohs(dport);
    e->saddr = saddr;
    e->daddr = daddr;

    bpf_ringbuf_submit(e, 0);
    return 0;
}

char LICENSE[] SEC("license") = "GPL";
```

### User-space skeleton (C)

```c
// main.c - load program, poll ring buffer, print
#include <bpf/libbpf.h>
#include <arpa/inet.h>
#include <signal.h>
#include <stdio.h>
#include <unistd.h>

#include "tcp_retransmit.skel.h"  // generated by bpftool/gen-skeleton

static volatile sig_atomic_t exiting;

static int handle_event(void *ctx, void *data, size_t len) {
    const struct event *e = data;
    char sbuf[INET_ADDRSTRLEN], dbuf[INET_ADDRSTRLEN];

    inet_ntop(AF_INET, &e->saddr, sbuf, sizeof(sbuf));
    inet_ntop(AF_INET, &e->daddr, dbuf, sizeof(dbuf));

    printf("retransmit %s:%u -> %s:%u at %.3f ms\n",
           sbuf, e->sport, dbuf, e->dport, e->ts_ns / 1e6);
    return 0;
}

static void sigint(int signo) { exiting = 1; }

int main() {
    struct ring_buffer *rb = NULL;
    struct tcp_retransmit_bpf *skel;
    int err;

    libbpf_set_strict_mode(LIBBPF_STRICT_ALL);
    signal(SIGINT, sigint);

    skel = tcp_retransmit_bpf__open_and_load();
    if (!skel) { fprintf(stderr, "open/load failed\n"); return 1; }

    err = tcp_retransmit_bpf__attach(skel);
    if (err) { fprintf(stderr, "attach failed: %d\n", err); return 1; }

    rb = ring_buffer__new(bpf_map__fd(skel->maps.rb), handle_event, NULL, NULL);
    if (!rb) { fprintf(stderr, "ringbuf create failed\n"); return 1; }

    printf("Capturing TCP retransmits... Ctrl-C to exit\n");
    while (!exiting) ring_buffer__poll(rb, 100);

    ring_buffer__free(rb);
    tcp_retransmit_bpf__destroy(skel);
    return 0;
}
```

**Why this matters:** CO-RE + libbpf gives you a production-friendly agent you can drop into diverse kernels (with BTF available), without recompiling per node.

---

## 8) How data moves: maps, perf buffers, ring buffers

eBPF’s data plane is half the story. The other half is getting that data out efficiently.

-   **Maps**: Key–value stores in kernel memory. Common types:

    -   `BPF_MAP_TYPE_HASH`, `ARRAY`: General storage for counters or state (e.g., start times).
    -   Per-CPU variants: Avoid locking; you aggregate in user space.
    -   LRU maps: Auto-eviction for bounded memory usage.
    -   `BPF_MAP_TYPE_STACK_TRACE`: Capture stack IDs; resolve in user space.
    -   `BPF_MAP_TYPE_LPM_TRIE`: Longest-prefix matching (useful for CIDR filters).

-   **Perf buffer**: Older stream mechanism; still widely used by BCC. Good, but involves extra copies.
-   **Ring buffer**: Newer, simpler, and lower overhead. Supports backpressure: if the user space consumer can’t keep up, reservations fail and you can drop with counters.

**Rule of thumb:** Use maps for _state_ and the ring buffer for _events_.

---

## 9) Safety first: the verifier and helpers

The BPF verifier ensures programs are safe to run in kernel context. It enforces:

-   Bounded loops and bounded call depth.
-   Verified memory access (pointer provenance tracking).
-   Stack and map bounds checks.
-   No uninitialized memory reads.

BPF programs also call into **helpers**—kernel-exposed functions like `bpf_ktime_get_ns`, `bpf_get_current_pid_tgid`, `bpf_map_lookup_elem`, `bpf_skc_to_tcp_sock`, and hash/CSUM helpers. The helper set depends on program type (e.g., XDP vs tracing).

**Pain avoided:** A bug in your BPF program won’t panic the kernel; it will be rejected at load time, with verbose diagnostics to guide fixes.

---

## 10) Patterns for low-overhead observability

eBPF gives you a power drill. Here’s how to avoid drilling through your foot:

-   **Filter early**: cgroup-based filtering keeps multi-tenant clusters isolated. Attach once; observe just the workloads you care about.
-   **Summarize in-kernel**: Use per-CPU hash maps to keep counters/percentiles (e.g., t-digest or HDR-like sketches via fixed buckets) and emit periodic summaries instead of per-event logs.
-   **Sample deliberately**: 1 in N syscalls may be plenty. For profiles, use `perf_event_open` + eBPF for sampling with symbolization offline.
-   **Use tail calls**: Compose small programs (e.g., “parse L4 → parse L7 → filter”) using tail calls to avoid monolithic code and keep verifier happy.
-   **Prefer tracepoints**: ABI-stable, safer across kernel versions. Fall back to kprobes only when you must.
-   **Embrace ring buffer backpressure**: Drop events before you drown user space. Track drops with counters and export them for alerting.

---

## 11) Cloud-native: what do popular projects actually do?

-   **Cilium & Hubble**: Use eBPF at TC/XDP for L3/L4 policy enforcement and flow visibility. Hubble taps these flows and kernel events to show “who-talks-to-whom,” with pod/namespace context baked in.
-   **Pixie**: Uses uprobes on common libraries and runtimes (e.g., OpenSSL, language runtimes) to extract application-level metadata—HTTP routes, SQL queries—often before/after encryption. You don’t have to modify your code, and it stitches process/container metadata to present service-level traces.
-   **Parca/Parca-Agent** and friends: Lean on eBPF + perf events for continuous profiling (CPU, memory), streaming stack traces with low overhead.

What’s common: early filtering in kernel space, CO-RE for portability, and careful data marshaling (ring buffers, per-CPU aggregation).

---

## 12) Shipping this in Kubernetes: deployment notes

The usual pattern is a **DaemonSet** running a privileged pod (or a pod with the right capabilities) on each node:

-   **Kernel + BTF**: Prefer kernels with BTF enabled (many distros now do). If missing, ship a BTF hub or a matching `vmlinux.h`.
-   **Capabilities**: Modern kernels split permissions among `CAP_BPF`, `CAP_PERFMON`, `CAP_NET_ADMIN` (for XDP/TC). Older setups default to `CAP_SYS_ADMIN`.
-   **bpffs**: Mount the BPF filesystem (`/sys/fs/bpf`) to share pinned maps and program handles across processes.
-   **Cgroup v2**: Enables richer per-cgroup accounting and filtering.
-   **Node heterogeneity**: CO-RE reduces per-kernel builds. Keep Arm64/AMD64 images if you’re multi-arch.

_Pro tip_: Ship your BPF object files alongside a small userspace agent. The agent handles attach/detach on pod start/stop, exposes Prometheus metrics for drop counts, and provides a control plane for dynamic filters.

---

## 13) What about security and multi-tenancy?

eBPF is powerful, so clusters must be careful:

-   **Who loads programs?** Restrict program loading to a trusted DaemonSet or operator. Admission control (and PSP/PSa replacements) should block arbitrary pods from `CAP_BPF`.
-   **Program types**: Tracing programs are lower risk than XDP/TC programs that can drop/redirect packets. Use program type-specific policy where possible.
-   **LSM hooks**: If you use LSM-based BPF, align with your security team; you’re now in the enforcement path.
-   **Resource limits**: Bound map sizes, set RLIMITs, and monitor verifier logs to catch misbehaving updates.

The good news: verifier + strict capabilities dramatically reduce blast radius compared to out-of-tree kernel modules.

---

## 14) Cost model: what does “low overhead” mean in practice?

Numbers depend on kernel versions, CPUs, and event rates, but the core levers are universal:

-   **Fixed cost per event**: Attach overhead + a few dozen–hundred cycles of BPF execution, plus any helper calls you make. Keep your program short.
-   **Copy cost**: Data moved from kernel to user space. Emit compact structs; avoid big strings; compress or summarize where possible.
-   **Aggregation**: Per-CPU maps let you aggregate with almost no contention; emit summaries every second instead of per-event.
-   **Backpressure**: If user space stalls, the ring buffer will drop reservations—track and alert on this.

Aim for _microseconds per event_ and low single-digit percentage CPU for cluster-wide agents. Validate with load tests on representative nodes.

---

## 15) Design walkthrough: end-to-end L7 request metric without app changes

Suppose you need HTTP request latency and status codes per service, but you can’t add middleware. One eBPF-first approach:

1. **Uprobes on common libraries**: Attach to `SSL_read`/`SSL_write` or language runtime HTTP parsers (e.g., Go’s `net/http` functions). For plaintext, uprobes on `read`/`write` in the runtime.
2. **Correlate with sockets**: Use `bpf_get_current_pid_tgid` + `bpf_get_current_uid_gid` to tag flows, and per-pid maps to correlate start/end timestamps.
3. **Filter by cgroup**: Only capture in target pods.
4. **In-kernel summaries**: Maintain histograms per HTTP route (keys hashed) and status code.
5. **Periodic export**: Every second, have user space drain and export histograms to Prometheus; reset maps atomically.

You’ve now built “tracing without traces”—L7 metrics with service labels—no code changes, low overhead.

---

## 16) Pitfalls and foot-guns (learned the hard way)

-   **Kernel ABI drift**: kprobes on private kernel functions can break across versions. Prefer tracepoints or CO-RE with careful BTF reads.
-   **Strings & big payloads**: Copying large payloads out of the kernel is slow. Extract only what you need; hash or truncate.
-   **Over-eager probes**: Hooking very hot paths (e.g., `sched:sched_switch`) can be costly if you emit per-event data. Summarize per CPU instead.
-   **Stack traces**: Resolving symbols in user space requires debuginfo; keep a symbol cache. For Go/Java, coordinate with language-specific unwinding.
-   **Time sources**: Use `bpf_ktime_get_ns()` consistently and convert in one place to avoid mixed units.
-   **Per-CPU maps**: Remember to aggregate across CPUs in user space; otherwise you’ll think some counters “reset randomly.”
-   **Verifier quirks**: Large helper chains or complex control flow can hit limits. Split logic and use tail calls.

---

## 17) eBPF + OpenTelemetry: friends, not rivals

eBPF isn’t a replacement for OpenTelemetry—think of it as a **data plane** that feeds your OTel pipelines with richer, more accurate signals. A pragmatic approach:

-   Keep OTel for app-level spans where you can instrument.
-   Use eBPF to fill in the gaps: kernel signals, network flows, auto-detected L7 metrics, continuous profiling.
-   Normalize in one place (e.g., an agent) and export to your existing backends (Prometheus, Tempo, Jaeger, etc.).

The result: better coverage with less developer friction.

---

## 18) A tiny checklist for your first production rollout

1. **Start with read-only tracing**: Tracepoints + uprobes. Defer XDP/TC until you need network enforcement.
2. **CO-RE from day one**: Avoid per-kernel build matrices.
3. **Per-CPU aggregation**: Histograms and counters in kernel; export every second.
4. **Backpressure metrics**: Track ring buffer drop counts and user space stall times.
5. **cgroup scoping**: Attach once per node; filter to target namespaces.
6. **Security posture**: Limit capabilities to the DaemonSet; pin BPFFS; audit program load/unload events.
7. **Load test**: Reproduce expected event rates; verify CPU headroom and zero alert noise.

---

## 19) Historical aside: from packet filters to a general-purpose VM

eBPF’s ancestor, classic BPF (cBPF), filtered packets for `tcpdump` in the early 1990s. Over decades, the model evolved: richer instructions, verifier, JIT, maps, and many program types beyond networking. Today, eBPF is a general-purpose, safe, in-kernel compute substrate—observability just happens to be one of the best early wins.

---

## 20) Key takeaways

-   **eBPF gives kernel-level truth with minimal overhead.** JIT + early filtering + per-CPU maps keep the hot path fast.
-   **Tracepoints and uprobes are your workhorses.** Prefer them for stability and wide coverage.
-   **CO-RE (with BTF) makes production viable.** Compile once, run across heterogeneous nodes.
-   **Design for summaries, not firehoses.** Aggregate in kernel; export periodically; measure drops.
-   **It fits your existing observability stack.** Feed Prometheus, Tempo, or your vendor of choice with better signals.

---

## Further reading & exploration

-   Read the kernel’s `Documentation/bpf` tree to understand program types and helpers.
-   Explore with `bpftrace` and BCC tools (e.g., `opensnoop`, `tcpconnect`, `biolatency`) on a dev node.
-   Build a tiny CO-RE agent with libbpf—start with a tracepoint like `sched:sched_process_exec`.
-   Kick the tires on Cilium/Hubble and Pixie in a kind cluster to see flows and L7 metadata without code changes.

---

### Appendix: tiny bpftrace cookbook

-   Count syscalls by process:

    ```bash
    bpftrace -e 'tracepoint:raw_syscalls:sys_enter { @[comm] = count(); }'
    ```

-   Top files opened (like `opensnoop` lite):

    ```bash
    bpftrace -e '
    kprobe:__x64_sys_openat { @f[comm, str(arg2)] = count(); }
    interval:s:5 { clear(@f); }'
    ```

-   TCP retransmits per destination (sampling):

    ```bash
    bpftrace -e '
    tracepoint:tcp:tcp_retransmit_skb { @[ntop(args->daddr)] = count(); }'
    ```

---

If you’re already collecting logs and traces, eBPF will feel like adding X-ray vision to your existing glasses. Start small, keep it safe, measure the cost, and you’ll find those “airport storms” a lot easier to land.
