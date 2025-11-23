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
    overlay_image: /assets/images/memory-bound-architecture/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/memory-bound-architecture/banner.png
title: "Memory‑Bound Architectures: Optimizing AI and Data Systems Beyond CPU Bottlenecks"
tags:
    - memory bound
    - ai
    - data engineer
---

Most performance horror stories start the same way:

> “The CPU is only at 40%, but everything is slow.”

You profile your system. The hottest stack frames are boring loops over arrays, or some innocent `memcpy`. You add more cores, a bigger GPU, a faster CPU… and your throughput barely moves.

Welcome to the world of **memory‑bound architectures** — where the real bottleneck isn’t how fast you can _compute_, but how fast you can _move bytes_.

Modern systems like DuckDB, ClickHouse, and PyTorch lean heavily into this reality. They treat memory as the primary scarce resource and design their runtimes, storage formats, and execution engines around cache efficiency and locality. ([ClickHouse][1])

This post is a guided tour of that world: what “memory‑bound” actually means, how the hardware shapes your software, and how AI and data systems exploit memory behavior to squeeze out obscene amounts of performance.

---

## 1. The uncomfortable truth: your CPU is mostly waiting

For decades, CPU performance grew exponentially. Memory… kind of didn’t.

Even today, a modern core can retire multiple instructions per cycle, but a DRAM access often costs **hundreds of cycles**. That growing gap between CPU speed and memory latency is widely known as the **memory wall**. ([embeddedtechlearn.com][2])

To keep the core busy, hardware adds a **memory hierarchy**:

-   Tiny, blazing‑fast L1 cache (tens of kilobytes)
-   Larger but slower L2/L3 caches (megabytes)
-   Much larger but far slower DRAM (gigabytes)
-   Maybe SSDs/disks beneath that

You can think of it like a chef:

-   The cutting board: registers
-   Ingredients on the counter: L1/L2
-   Pantry in the kitchen: DRAM
-   Storage room down the hall: disk

The chef is very fast with the knife, but if they walk to the storage room for every onion, you’re not eating tonight.

Over time, the hierarchy becomes deep and complex, precisely because **raw DRAM cannot keep up with core throughput**. ([Cambridge University Press & Assessment][3])

That’s why “CPU at 40%” is often a symptom, not a comfort: the core is idle because it’s waiting on data.

---

## 2. Compute‑bound vs memory‑bound: the roofline view

To reason about this, performance engineers often use the **Roofline model**. ([NERSC Documentation][4])

It plots:

-   **X‑axis**: _Arithmetic intensity_ – how many operations you do per byte of data (FLOPs/byte or ops/byte).
-   **Y‑axis**: _Achieved performance_ – how many FLOPs per second you’re getting.

The hardware gives you two ceilings (“roofs”):

1. **Compute roof** — max FLOPs/s the CPU or GPU can theoretically do.
2. **Memory roof** — max FLOPs/s given the memory bandwidth and your arithmetic intensity.

At low arithmetic intensity (few ops per byte), performance is limited by how fast you can **move data**, not how fast you can **calculate** on it. You’re in the **memory‑bound** region.

At high arithmetic intensity (many ops per byte), you eventually hit the compute roof. Now you’re **compute‑bound**: more bandwidth won’t help, but faster cores or specialized units might. ([NERSC Documentation][4])

Deep learning is a perfect example:

-   **Matrix multiplications / convolutions**: Very high arithmetic intensity → often compute‑bound (especially on GPUs).
-   **Elementwise ops (activations, pointwise transforms)**: One or two ops per element → often **memory‑bound**.

The PyTorch docs explicitly call out that typical pointwise operations are memory‑bound and that fusing them into a single kernel is critical for performance. ([PyTorch Documentation][5])

The core insight:

> For many workloads, **you won’t go faster by adding more ALUs**. You’ll go faster by **moving fewer bytes** or **reusing bytes better**.

---

## 3. A five‑minute tour of the memory hierarchy (for programmers)

Okay, but what does “moving fewer bytes” actually look like?

At a very high level:

-   **Registers** — essentially free, but you only get a handful.
-   **L1 cache** — a few cycles to access, but very small.
-   **L2/L3 cache** — more capacity, higher latency.
-   **DRAM** — orders of magnitude slower than L1 in terms of latency and limited in bandwidth.
-   **Disk/SSD** — far slower again, but massive capacity.

Caches move data around in **cache lines** — usually 64 bytes. When you load `a[123]`, the CPU actually fetches a whole line containing neighboring elements.

Two core principles fall out:

-   **Spatial locality**: Access neighboring data → you already paid for that cache line.
-   **Temporal locality**: Reuse data soon → it stays hot in the cache.

Modern memory hierarchy design explicitly tries to exploit these patterns. ([Cambridge University Press & Assessment][3])

Your job, as a systems programmer, is to make those principles _true_ in your code.

---

## 4. Data layout: how to accidentally throttle your own CPU

Let’s look at a small example.

Say you have a bunch of 3D points, and you want to compute the sum of their `z` coordinates.

### Version 1: Array of structs (AoS)

```c
typedef struct {
    float x;
    float y;
    float z;
    int   id;
} Point;

float sum_z(const Point* points, size_t n) {
    float acc = 0.0f;
    for (size_t i = 0; i < n; ++i) {
        acc += points[i].z;
    }
    return acc;
}
```

This is idiomatic and easy to read.

But the memory pattern is:

-   Each `Point` is, say, 16 bytes.
-   You only need the `z` field (4 bytes), but the CPU fetches entire 64‑byte cache lines.
-   That cache line may contain `x`, `y`, `id`, and parts of neighboring points.

You’re dragging useless data through the hierarchy. The more fields you don’t use, the more you waste your cache and memory bandwidth.

### Version 2: Struct of arrays (SoA)

```c
typedef struct {
    float *x;
    float *y;
    float *z;
    int   *id;
} PointSoA;

float sum_z_soa(const PointSoA* points, size_t n) {
    float acc = 0.0f;
    float *z = points->z;

    for (size_t i = 0; i < n; ++i) {
        acc += z[i];
    }
    return acc;
}
```

Now, all `z` values are contiguous. You stream through exactly the bytes you care about. The CPU can prefetch efficiently; vector units can load multiple `z` values at once; cache lines are full of useful data.

For big `n`, this can be _dramatically_ faster, even though the algorithm is the same `O(n)` loop. You didn’t change the math; you changed the bytes.

This is exactly the kind of rearrangement that underpins columnar data systems and vectorized execution engines.

---

## 5. DuckDB, ClickHouse, and the rise of cache‑centric databases

Analytical databases like DuckDB and ClickHouse are basically giant case studies in “memory‑bound thinking.”

### Columnar storage: SoA at scale

Both systems store data **column‑wise** rather than row‑wise for analytics: you read many rows but only a few columns. With columnar storage, each column is like one big SoA array. ([ClickHouse][1])

That buys you:

-   **Spatial locality**: Scans touch sequential memory for the few columns you care about.
-   **Selective I/O**: You skip entire columns you don’t need, so fewer bytes move through DRAM and caching layers.
-   **Better compression**: Columns with similar values compress extremely well, and compression further reduces bytes moved from disk/DRAM.

### Vectorized execution and data chunks

DuckDB processes data in **vectors** — batches of column values (often 2048 rows per vector) grouped into `DataChunk`s. Each operator works on these chunks, keeping intermediate working sets small enough to fit comfortably in caches. ([DeepWiki][6])

Why is this powerful?

-   You amortize interpretation/virtual call overhead across many rows.
-   You expose dense loops over contiguous arrays → compilers can auto‑vectorize; CPU prefetchers do the right thing.
-   You keep hot data (current vectors) in L1/L2, rather than streaming a row at a time through the entire plan.

ClickHouse follows a similar pattern: it uses **block‑oriented**, columnar processing, vectorized execution, and SIMD instructions to maximize CPU cache hit rates and reduce memory traffic. ([ClickHouse][1])

### Example: filter and aggregate

Conceptually, a simple SQL like:

```sql
SELECT user_id, SUM(amount)
FROM payments
WHERE status = 'OK'
GROUP BY user_id;
```

In a row‑store:

-   You fetch entire rows: `user_id`, `amount`, `status`, plus every other column.
-   Filters interleave with decoding row layouts.
-   Cache lines are full of columns you don’t need.

In a columnar, vectorized engine:

-   You scan `status` as a single column, produce a bitmask of “rows to keep”.
-   You apply that mask to `user_id` and `amount` vectors.
-   You aggregate `amount` by `user_id` on compact, filtered vectors.

Everything is “tight loops over arrays”, not “pointer‑chasing over heap objects”.

The math didn’t change. The **bytes** did.

---

## 6. AI workloads: PyTorch, kernel fusion, and the memory wall on GPUs

It’s tempting to think GPUs escape this because their memory bandwidth is enormous. But the same principles bite there too.

Deep learning performance analysis using Roofline models on GPUs shows that many kernels fall squarely into the memory‑bound region: their FLOPs/byte are too low to saturate compute units, so the limiting factor is global memory bandwidth. ([arXiv][7])

PyTorch’s own performance tuning guide makes this explicit:

-   **Pointwise operations** (e.g., adding a bias, applying `tanh`, scaling by a constant) are often **memory‑bound**.
-   Naively, each op launches a separate kernel: load → compute → store.
-   That means _multiple_ full passes over the tensor in global memory. ([PyTorch Documentation][5])

Consider this toy example:

```python
# Naive: 3 kernels
y = torch.sin(x)     # 1: read x, write tmp1
y = y * 0.5          # 2: read tmp1, write tmp2
y = torch.relu(y)    # 3: read tmp2, write y
```

You’ve done only a handful of FLOPs per element, but you streamed the entire tensor from global memory **three times**.

Now compare a fused version:

```python
# Fused: ideally 1 kernel
y = torch.relu(torch.sin(x) * 0.5)
```

A fused kernel can:

-   Load each element of `x` once.
-   Perform `sin`, multiply by `0.5`, then apply `relu` all in registers.
-   Store the result once.

Same math, but you cut global memory traffic by ~3×. You move closer to the bandwidth roofline, and overall throughput increases without changing the number of compute units.

This is why:

-   Frameworks invest in **kernel fusion** (TorchScript, nvFuser, XLA, etc.).
-   Libraries introduce **fused optimizers** and activation blocks.
-   Layout choices (e.g., channels‑last tensors) are optimized for coalesced memory accesses and better cache behavior on both CPU and GPU.

The theme is exactly the same as with DuckDB/ClickHouse:

> Do more work per byte loaded.
> Touch each byte as few times as possible.

---

## 7. Designing for memory locality: patterns that actually matter

So what does “design for memory‑bound architectures” look like in practice?

Here are some patterns that show up across AI frameworks and data systems.

### 7.1 Fewer passes over data

-   Combine multiple logical operations into a **single physical pass**.
-   In databases: push filters down so you discard rows early, and fuse filter + projection + simple expressions into one vectorized pipeline.
-   In AI: use fused kernels for activation + bias + normalization when possible; avoid long chains of separate pointwise ops.

Look suspiciously at any code that walks the same array multiple times.

### 7.2 Columnar / SoA layouts for analytics

-   Prefer **struct‑of‑arrays** for workloads that touch a subset of fields.
-   Store analytics data **column‑wise**, not row‑wise.
-   Group fixed‑width columns; handle variable‑width (strings, JSON) as separate offset + data buffers.

DuckDB’s `Vector` and `DataChunk` abstractions, and ClickHouse’s columnar blocks, are both embodiments of SoA at the engine level. ([DeepWiki][6])

### 7.3 Batching and vectorized execution

-   Process data in **batches** that fit comfortably in L1/L2 caches.
-   Avoid per‑row virtual calls or function dispatch inside tight loops.
-   Use flat loops over arrays so compilers can unroll + vectorize.

Vectorized engines (DuckDB, ClickHouse) use batch sizes chosen explicitly to play nice with caches and vector units. ([DuckDB][8])

### 7.4 Tiling and blocking

For algorithms like matrix multiply, convolution, or joins:

-   Break data into tiles so the working set of each inner loop fits in cache.
-   Reuse tiles as much as possible before moving on.

The classic “blocked matrix multiply” is essentially: “keep submatrices in cache; don’t thrash”.

### 7.5 Compression as a bandwidth amplifier

Compression isn’t just about saving disk.

-   Columnar systems compress blocks to reduce **bytes read/written**, then decompress within caches.
-   Some formats support lightweight encoding (run‑length, bit‑packing, dictionary) that’s cheap to decode and very cache‑friendly.

The net effect: more useful data per cache line / DRAM burst.

ClickHouse explicitly uses compressed columnar blocks to reduce both storage and I/O, improving effective bandwidth. ([Instaclustr][9])

### 7.6 NUMA awareness

On multi‑socket systems:

-   DRAM is attached to specific CPU sockets (NUMA nodes).
-   Cross‑socket memory access is slower and can reduce effective bandwidth.

Partition and pin threads so they primarily access memory from their “local” NUMA node. Many OLAP systems and inference servers do this under the hood.

---

## 8. A tiny “roofline” mindset for your own code

You don’t need a full HPC setup to think like this.

When you look at a hot loop, ask:

1. **What’s the arithmetic intensity?**
   Roughly:
   `ops_per_element / bytes_per_element_moved`

2. **Where is the data?**
   Is it contiguous? Strided? Pointer‑chased? Is the working set bigger than L2?

3. **How many passes do I take over it?**
   Can I fuse some passes?

4. **Are my hot loops simple enough to auto‑vectorize?**
   Remove branches, function pointers, and weird control flow from inner loops.

Here’s a concrete before/after in C‑style pseudocode for a simple analytics transform:

### Before: three passes, row‑oriented

```c
typedef struct {
    int   user_id;
    int   status;
    float amount;
} Row;

void process(Row* rows, size_t n) {
    // 1. Filter
    for (size_t i = 0; i < n; ++i)
        if (rows[i].status != OK) rows[i].amount = 0;

    // 2. Apply discount
    for (size_t i = 0; i < n; ++i)
        rows[i].amount *= 0.9f;

    // 3. Sum
    float total = 0;
    for (size_t i = 0; i < n; ++i)
        total += rows[i].amount;

    // use total...
}
```

### After: one pass, SoA

```c
typedef struct {
    int   *user_id;
    int   *status;
    float *amount;
} Columns;

float process_soa(const Columns* cols, size_t n) {
    float total = 0.0f;
    int   *status = cols->status;
    float *amount = cols->amount;

    for (size_t i = 0; i < n; ++i) {
        if (status[i] == OK) {
            float a = amount[i] * 0.9f;
            amount[i] = a;
            total += a;
        } else {
            amount[i] = 0.0f;
        }
    }
    return total;
}
```

Same logic:

-   But now you make **one pass** over `status` and `amount`.
-   Data is **columnar**, so each cache line is full of relevant values.
-   Inner loop is tight and predictable → better auto‑vectorization and prefetching.

You’ve turned a potentially memory‑bound mess into something that makes much better use of the hierarchy.

---

## 9. A practical checklist for performance‑minded engineers

When you’re triaging a slow system — whether it’s a model training loop, an analytics service, or some home‑grown data pipeline — here’s a quick checklist.

### Step 1: Confirm you’re memory‑bound

-   Use basic profiling tools to see:

    -   CPU utilization per core.
    -   Cache miss rates, memory bandwidth counters if available.

-   Consult a Roofline plot for your hardware if you can (many tools and docs exist for CPUs and GPUs). ([NERSC Documentation][4])

If you’re nowhere near peak FLOPs, but close to peak memory bandwidth, you’re memory‑bound.

### Step 2: Look for wasteful data movement

-   Multiple passes over the same arrays?
-   Row‑oriented access when you only use a few fields?
-   Pointer‑heavy data structures in hot loops?
-   Large temporary tensors that get written and read again immediately?

### Step 3: Apply memory‑centric transformations

-   **Fuse kernels/passes** where possible.
-   Switch to **columnar/SoA** layouts for analytics or SIMD‑amenable code.
-   Introduce **tiling** for algorithms with large matrices/tensors.
-   Ensure **contiguous** or at least well‑strided memory access in inner loops.
-   Take advantage of **framework features**:

    -   DuckDB/ClickHouse: let the engine do vectorization and predicate pushdown; avoid forcing row‑by‑row UDFs where not necessary.
    -   PyTorch: use channels‑last layouts where recommended, enable kernel fusion / graph modes when stable for your workload. ([endjin.com][10])

### Step 4: Re‑measure and iterate

-   Re‑profile with the same tools.
-   See if cache miss rates and memory bandwidth usage improved.
-   Use that feedback to decide if you should optimize layout further or if you’ve moved into the compute‑bound regime (in which case, micro‑optimizing memory isn’t the next lever).

---

## 10. Why this matters _now_

The reason memory‑bound thinking is having a moment:

-   **CPU and GPU compute has grown absurdly fast** (SIMD, AVX‑512, tensor cores, etc.).
-   **Memory latency and bandwidth have not kept pace** to the same degree. ([VLSI][11])
-   Workloads are becoming more **data‑hungry** (deep learning, real‑time analytics, feature stores).

Systems like DuckDB and ClickHouse show how far you can go on a single machine when you design explicitly around caches, columnar layouts, and vectorization. ([endjin.com][10])

Frameworks like PyTorch show that even on GPUs, where compute units are abundant, you still win big by touching memory fewer times and thinking in terms of arithmetic intensity and fusion. ([PyTorch Documentation][5])

The future isn’t just “more FLOPs.” It’s **more FLOPs per byte**.

---

## 11. Further reading

If you want to go deeper, here are some great starting points:

-   **Roofline model**

    -   NERSC documentation on the Roofline performance model. ([NERSC Documentation][4])

-   **Memory hierarchy and the memory wall**

    -   Recent overviews of the memory hierarchy and the memory wall in modern architectures. ([VLSI][11])

-   **DuckDB internals**

    -   “DuckDB in Depth: How It Works and What Makes It Fast” and DuckDB’s execution framework docs. ([endjin.com][10])

-   **ClickHouse architecture**

    -   Official architecture docs and blog posts on its columnar, vectorized design. ([ClickHouse][1])

-   **PyTorch performance**

    -   PyTorch’s performance tuning and memory‑bound kernel fusion guide. ([PyTorch Documentation][5])

If you build systems where performance matters — AI pipelines, analytics engines, storage layers — it’s worth adopting this mindset:

> **First, understand how your code moves bytes.
> Only then worry about how it moves FLOPs.**

[1]: https://clickhouse.com/clickhouse?utm_source=thinhdanggroup.github.io "Real-Time Data Analytics Platform | ClickHouse"
[2]: https://www.embeddedtechlearn.com/2025/07/cpu-cache-memory.html?utm_source=thinhdanggroup.github.io "Deep Dive into CPU Cache Memory: Solving the Memory Wall"
[3]: https://www.cambridge.org/highereducation/books/parallel-computer-organization-and-design/8B85D00222C5545A6EB590A80031AE01/memory-hierarchies/9CA7A630154B635201A34FB43BE56C92?utm_source=thinhdanggroup.github.io "Memory hierarchies | Parallel Computer Organization and Design | Higher Education from ..."
[4]: https://docs.nersc.gov/tools/performance/roofline/?utm_source=thinhdanggroup.github.io "Roofline Performance Model - NERSC Documentation"
[5]: https://docs.pytorch.org/tutorials/recipes/recipes/tuning_guide.html?utm_source=thinhdanggroup.github.io "Performance Tuning Guide - PyTorch"
[6]: https://deepwiki.com/duckdb/duckdb/4.1-execution-framework?utm_source=thinhdanggroup.github.io "Type System and Vectors | duckdb/duckdb | DeepWiki"
[7]: https://arxiv.org/pdf/2009.05257?utm_source=thinhdanggroup.github.io "Hierarchical Rooﬂine Performance Analysis for Deep Learning Applicatio - arXiv.org"
[8]: https://duckdb.org/science/data-chunk-compaction/?utm_source=thinhdanggroup.github.io "Data Chunk Compaction in Vectorized Execution – DuckDB"
[9]: https://www.instaclustr.com/education/clickhouse/clickhouse-architecture-4-key-components-and-optimization-tips/?utm_source=thinhdanggroup.github.io "ClickHouse architecture: 4 key components and optimization tips"
[10]: https://endjin.com/blog/2025/04/duckdb-in-depth-how-it-works-what-makes-it-fast?utm_source=thinhdanggroup.github.io "DuckDB in Depth: How It Works and What Makes It Fast | endjin"
[11]: https://www.vlsi.kr/memory-hierarchy-the-memory-wall-and-the-pivotal-role-of-memory-semiconductors/?utm_source=thinhdanggroup.github.io "Memory Hierarchy, the Memory Wall, and the Pivotal Role of Memory Semiconductors"
