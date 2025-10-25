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
    overlay_image: /assets/images/python313-free-threading/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/python313-free-threading/banner.png
title: "Breaking Down Python 3.13’s Experimental Free‑Threading Mode"
tags:
    - Python 3.13
    - Free-Threading
---

_The year the GIL blinked._ With Python 3.13, CPython gained an **experimental “free‑threading” build** that can run threads truly in parallel on multiple cores. If you’ve ever reached for `multiprocessing` as a workaround for CPU‑bound work—or told yourself “threads are great… for I/O”—this is a big deal. In this post, we’ll unpack what “free‑threading” means, how to try it, the caveats, and what changed under the hood to make it possible. ([Python documentation][1])

---

## Why we had a GIL in the first place (and why we’re poking it now)

CPython’s historical bargain has been: keep the interpreter simple and fast for single‑threaded programs by guarding the runtime with one **Global Interpreter Lock (GIL)**. Reference counting, object models, and large swaths of C API code assumed a single “owner” at a time. That design has served Python well for decades, but it also meant **only one thread could execute Python bytecode at once**. Parallel CPU utilization required processes, not threads.

The push to loosen that constraint has been incremental:

-   **PEP 684 (Per‑Interpreter GIL)** in Python 3.12 isolated interpreter state enough that different _subinterpreters_ can each have their own GIL. That didn’t help typical single‑interpreter programs, but it removed architectural roadblocks. ([Python Enhancement Proposals (PEPs)][2])
-   **PEP 703 (Making the GIL optional)** proposed a build of CPython with the GIL disabled, plus runtime and C‑API changes to keep things safe. That proposal became the foundation of the **free‑threaded** build introduced experimentally in 3.13. ([Python Enhancement Proposals (PEPs)][3])

---

## How to try free‑threading today

**There are two moving parts to know about: a build, and a runtime switch.**

1. **Install a free‑threaded build.**
   On macOS and Windows, the official installers include an optional “free‑threaded Python” component. On POSIX, you can build from source using `./configure --disable-gil`. Installations typically expose a separate binary named like `python3.13t` (note the **`t`** suffix). ([Python documentation][1])

2. **Choose whether the GIL is on or off at runtime.**
   Even with a free‑threaded build, you can still **enable or disable** the GIL per process:

    ```bash
    # Run with GIL disabled (free-threaded):
    python3.13t -X gil=0 your_script.py
    # …or equivalently:
    PYTHON_GIL=0 python3.13t your_script.py

    # Force the GIL back on (for compatibility testing):
    python3.13t -X gil=1 your_script.py
    ```

    If you import a C extension that **isn’t** marked free‑threading‑safe, CPython will automatically **re‑enable** the GIL (and warn you)—unless you **explicitly** disabled it with `-X gil=0`/`PYTHON_GIL=0`. You’ll also want **pip 24.1+** for installing extension packages on the free‑threaded ABI. ([Python documentation][4])

3. **Check what you’re running.**

    ```python
    # detect_free_threading.py
    import sys, sysconfig
    print(sys.version)
    print("GIL enabled?   ", sys._is_gil_enabled())
    print("Build supports free-threading?",
          sysconfig.get_config_var("Py_GIL_DISABLED") == 1)
    ```

    If your interpreter supports it, `python -VV` will include “experimental free‑threading build”. The `sys._is_gil_enabled()` probe tells you whether the GIL is currently on. ([Python documentation][1])

> **Heads‑up on packaging/ABI:** on POSIX the `pkg-config` filename carries the ABI flag; for example, the free‑threaded build installs `python-3.13t.pc`. That `t` also shows up in wheel tags (e.g., `cp313t`). ([Python documentation][4])

If you’re on Linux or prefer curated guidance, the community “Python Free‑Threading Guide” tracks installers and distro packages (Fedora, Nixpkgs, Homebrew, Anaconda/conda‑forge) and provides CI‑friendly commands. It also tracks ecosystem support as more packages publish `*t` wheels. ([py-free-threading.github.io][5])

---

## A tiny experiment: CPU‑bound threads that really scale

Let’s take a stereotypical CPU‑bound task—counting primes—run it on N threads, and time the results. (Yes, this is intentionally inefficient pure‑Python; the point is to stress the interpreter.)

```python
# primes_threads.py
import os, time, math
from concurrent.futures import ThreadPoolExecutor

def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    r = int(math.isqrt(n))
    f = 3
    while f <= r:
        if n % f == 0:
            return False
        f += 2
    return True

def count_primes(start: int, stop: int) -> int:
    # Tight loop, heavy on Python bytecode
    return sum(1 for x in range(start, stop) if is_prime(x))

def main():
    N = os.cpu_count() or 4
    LIMIT = 300_000
    chunk = LIMIT // N
    ranges = [(i*chunk, (i+1)*chunk) for i in range(N)]
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=N) as ex:
        total = sum(ex.map(lambda rs: count_primes(*rs), ranges))
    dt = time.perf_counter() - t0
    print(f"Threads: {N}, primes < {LIMIT}: {total}, {dt:.2f}s")

if __name__ == "__main__":
    main()
```

Try three runs:

```bash
# 1) Regular CPython (GIL on, single-core execution)
python3.13 primes_threads.py

# 2) Free-threaded build, but force GIL on (control group)
python3.13t -X gil=1 primes_threads.py

# 3) Free-threaded build with GIL off: threads run truly in parallel
python3.13t -X gil=0 primes_threads.py
```

On a multi‑core machine, (3) should show a much shorter wall‑clock time than (1) and (2)—because with the GIL off, the worker threads can execute Python code on different cores simultaneously. You’ll often see speedups near the number of cores for pure‑Python CPU workloads (bounded by cache/memory effects). For I/O‑bound work, expect little change: Python has long released the GIL around blocking I/O, so **I/O concurrency already scales** with the regular interpreter.

---

## The fine print: performance and limitations

Free‑threading is **experimental** in 3.13. It works, but it’s not yet the default—and you should expect a **single‑thread overhead** on pure‑Python code. For 3.13 the docs report about **~40% on the `pyperformance` suite**, largely because the **specializing adaptive interpreter (PEP 659)** is disabled in the free‑threaded build; the plan is to re‑enable it safely in future releases and reduce the overhead. If your workload spends most time in C extensions or I/O, the impact is smaller. ([Python documentation][1])

There are some **behavioral constraints** worth knowing:

-   **Built‑in containers lock internally.** Types like `list`, `dict`, and `set` use internal locks to protect against concurrent mutation, aiming to preserve the same “works in practice” semantics people relied on implicitly under the GIL. Still, don’t rely on unspecified behavior: **explicit locks** (e.g., `threading.Lock`) are recommended for correctness. ([Python documentation][6])
-   **Some objects become “immortal”.** In 3.13’s free‑threaded build, module‑level `function`/`code`/`type` objects (and module dicts) are made _immortal_ after the first thread starts: their refcounts don’t change and they’re never deallocated. This avoids hot refcount contention but means programs that create many of those objects may see **higher memory usage**. Work to remove or narrow this behavior continues in 3.14+. Numeric and string literals (and `sys.intern()` results) are also treated specially. ([Python documentation][1])
-   **Frames and iterators:**

    -   Accessing a **frame** object from another thread isn’t safe (e.g., `sys._current_frames()` is generally a no‑go).
    -   Sharing **the same iterator** object across threads is not safe—threads may skip or duplicate items, or crash. Prefer giving each thread its own iterator, converting to a list ahead of time, or using a `queue.Queue`. ([Python documentation][1])

### A quick “don’t do this” (and a fix)

**Problematic: shared iterator**

```python
# NOT SAFE in a free-threaded build:
shared_it = iter(range(10_000_000))

def worker():
    for x in shared_it:     # multiple threads racing one iterator
        pass
```

**Safer options:**

```python
# 1) Give each thread its own range/iterator
def worker(start, stop):
    for x in range(start, stop):
        pass

# 2) Or push work units through a Queue
from queue import Queue
q = Queue()
for x in range(10_000_000):
    q.put(x)
def worker_from_queue():
    while True:
        try:
            x = q.get_nowait()
        except Exception:
            break
        finally:
            q.task_done()
```

---

## What changed under the hood? (A tour without spelunking C code)

Removing the GIL is less about _one_ change and more about a **constellation of cooperating mechanisms**. Three standouts affect regular Python code and many C extensions.

### 1) Making the object model thread‑safe

Historically the GIL implicitly serialized refcount updates and many object operations. Without it:

-   **Reference counting and lifetime:** 3.13’s free‑threaded build takes a conservative path (e.g., “immortal” objects, see above) to avoid high‑contention hot spots. You’ll also see **internal locks** around operations on built‑in containers, so that e.g. `list.append()` remains safe to call from multiple threads (though your program’s higher‑level invariants still need application‑level locks). ([Python documentation][6])
-   **Interpreter optimizations:** the adaptive tiering engine (PEP 659) currently stays off in the free‑threaded build while it’s retooled for safe sharing. That’s the core reason for the single‑thread overhead today. ([Python documentation][1])

### 2) A new contract with extension modules

Extension modules must **opt into** running with the GIL disabled. If an extension isn’t marked, importing it will **turn the GIL back on** (with a warning) so it can keep working as‑is.

For authors:

-   If you use **multi‑phase init** (`PyModuleDef_Init`), set the **`Py_mod_gil`** slot to `Py_MOD_GIL_NOT_USED`.
-   If you use **single‑phase init** (`PyModule_Create` style), call **`PyUnstable_Module_SetGIL(module, Py_MOD_GIL_NOT_USED)`** under `#ifdef Py_GIL_DISABLED`.
-   Prefer APIs that return **strong references** rather than borrowed ones (e.g., `PyList_GetItemRef()` instead of `PyList_GetItem()`), and be mindful of macros that don’t lock or check errors (e.g., `PyList_GET_ITEM`).
-   Some operations require **critical sections**. CPython provides `Py_BEGIN_CRITICAL_SECTION(obj)` / `Py_END_CRITICAL_SECTION()`, and a variant for two objects, to guard regions that in a GIL’d world were implicitly safe. These are no‑ops on non‑free‑threaded builds, so you can write one codebase that works both ways. ([Python documentation][7])

> **Tip:** The project‑maintained free‑threading guide has porting checklists and CI examples, and a tracker of which libraries already ship `*t` wheels. Great starting points if you maintain C/C++/Rust extensions. ([py-free-threading.github.io][8])

### 3) Runtime switches and compatibility escape hatches

Why does CPython let the free‑threaded build _re‑enable_ the GIL? Because backwards compatibility across the ecosystem matters. The runtime knobs (`-X gil`, `PYTHON_GIL`) let you **mix and match**: run a free‑threaded build with GIL off when your dependency stack supports it, or flip it on when some extension hasn’t been ported yet. pip’s newer releases also understand the `t` ABI when resolving wheels. ([Python documentation][4])

---

## When (and when not) to use free‑threading

**Use it if…**

-   Your workload is **pure‑Python CPU‑bound** and you want to scale across cores with threads. (Think: text processing, custom data transforms, domain‑specific compute that isn’t a NumPy call.)
-   You have **many short‑lived CPU tasks** where threads’ lower spawn/teardown overhead (vs processes) matters to throughput.
-   You’re building a **hybrid app** where Python threads coordinate work and do some Python‑level compute in between calls into native code.

**Stick with the default build (for now) if…**

-   Your workload is mostly **I/O‑bound** (networking, file I/O). Regular CPython already releases the GIL around I/O, so you probably won’t see meaningful differences.
-   You rely on extensions that **re‑enable the GIL** today. (Check the ecosystem trackers.) ([py-free-threading.github.io][8])
-   You need **peak single‑thread performance** and your app doesn’t meaningfully benefit from parallel Python execution yet. The ~40% overhead in 3.13 can be a deal‑breaker for single‑core tight loops. ([Python documentation][1])

---

## Practical recipes and gotchas

### Detect support at import time

If you’re publishing a library that wants to “do the right thing”:

```python
# runtime_detection.py
import sys, sysconfig, warnings

SUPPORTS_FREE_THREADING_BUILD = sysconfig.get_config_var("Py_GIL_DISABLED") == 1
GIL_ON = sys._is_gil_enabled()

if SUPPORTS_FREE_THREADING_BUILD and not GIL_ON:
    # Possibly enable extra concurrency features
    pass
else:
    warnings.warn(
        "Running with the GIL enabled; parallel thread support is limited."
    )
```

Make your behavior **feature‑driven** instead of version‑driven: a 3.13 regular build and a 3.13 free‑threaded build are both “3.13” but behave differently. ([Python documentation][1])

### Avoid shared iterators; use queues or per‑thread ranges

We saw earlier how sharing one iterator across threads is unsafe. Either **partition the work** deterministically (ranges per thread) or **push units** through a `queue.Queue`. This is both correct and explicit.

### Guard global caches

Libraries often keep **global dict/list/set caches**. Under the GIL those were “accidentally safe.” Under free‑threading, protect them:

```python
from threading import RLock
_cache_lock = RLock()
_cache = {}

def get_or_compute(key):
    with _cache_lock:
        val = _cache.get(key)
        if val is None:
            val = compute(key)  # may release the GIL in extensions; that's OK
            _cache[key] = val
        return val
```

Even though built‑in containers lock internally for individual operations, your **higher‑level invariants** (e.g., “check‑then‑insert is atomic”) still need explicit synchronization. ([Python documentation][6])

---

## Notes for extension authors (C/C++/Rust)

If you write or maintain extensions:

-   **Mark your module** as free‑threading‑compatible (`Py_mod_gil` or `PyUnstable_Module_SetGIL`) or the interpreter will re‑enable the GIL on import. ([Python documentation][7])
-   **Audit APIs** that return **borrowed references** (e.g., `PyList_GetItem`, `PyDict_GetItem`); prefer the new `*Ref` variants that return owned references. This reduces refcount races. ([Python documentation][7])
-   **Be careful with macros** like `PyList_GET_ITEM`—they don’t lock or check errors. If the underlying object can be mutated concurrently, wrap accesses with **critical sections**. (There’s also a `*_CRITICAL_SECTION2` form for locking two objects together.) ([Python documentation][7])
-   **Memory domains matter.** Use `PyObject_*` allocators **only** for Python objects; use `PyMem_*` for raw buffers. The free‑threaded build tightens this old best practice into a requirement. ([Python documentation][7])

> **Tooling:** The ecosystem maintains a live **compatibility tracker** and install recipes, plus guidance for setting up CI and sanitizers (TSan). Check those first; many common stacks (NumPy, SciPy, pandas, pybind11, Cython, PyO3, etc.) are actively publishing `*t` wheels. ([py-free-threading.github.io][8])

---

## Frequently asked “but what about…?”

**Does free‑threading make `asyncio` obsolete?**
No. `asyncio` remains a great fit for high‑concurrency I/O where tasks are mostly waiting. Free‑threading helps **CPU‑bound** work run in parallel _in the same process_—a different niche.

**Will my code be faster without changes?**
If it’s CPU‑bound and uses threads constructively, likely yes. If it wasn’t threaded or is I/O‑bound, probably not. Also remember the **single‑thread overhead** in 3.13; if you flip the GIL off without adding thread‑level parallelism, you may see slowdowns. ([Python documentation][1])

**What if one dependency isn’t free‑threading‑ready?**
Run the free‑threaded build **with the GIL on** (`-X gil=1`) until that dependency catches up, or isolate it behind a process boundary. The runtime switch exists exactly for this transition period. ([Python documentation][4])

---

## Section summaries

-   **Motivation:** The GIL simplified CPython’s internals but serialized Python bytecode. PEP 684 laid groundwork (per‑interpreter GIL); PEP 703 made the GIL **optional** in a special build. ([Python Enhancement Proposals (PEPs)][2])
-   **Getting started:** Install a **free‑threaded** build (`python3.13t`), toggle the GIL with `-X gil`/`PYTHON_GIL`, and detect support with `sys._is_gil_enabled()` and `sysconfig.get_config_var("Py_GIL_DISABLED")`. ([Python documentation][4])
-   **Behavior today:** Multicore **CPU‑bound** threads can finally scale; single‑threaded pure‑Python code pays an overhead in 3.13 (~40%) due to the (temporarily) disabled adaptive interpreter. ([Python documentation][1])
-   **Internals:** Built‑ins use **internal locks**; some core objects are **immortalized** to lower contention; and the C API gains **critical sections** and opt‑in markers for running without the GIL. ([Python documentation][6])
-   **Ecosystem:** Many projects now publish `*t` wheels; use the trackers to check status; the ABI exposes a `t` suffix. ([py-free-threading.github.io][8])

---

## Key takeaways

1. **Free‑threading is real and usable in 3.13**, but it’s **opt‑in** (separate build) and still experimental. Expect trade‑offs. ([Python documentation][1])
2. **Threads can finally speed up pure‑Python CPU work** across cores. If you can split your CPU‑bound task into parallel chunks, you no longer need processes just to escape the GIL.
3. **Write thread‑safe Python anyway.** Internal locks in built‑ins are not a contractual guarantee; protect your own invariants explicitly. ([Python documentation][6])
4. **C extensions need to opt in.** Until they do, the runtime may re‑enable the GIL when you import them. ([Python documentation][4])
5. **The story will get faster.** The ~40% single‑thread overhead in 3.13 is expected to come down as the specializing interpreter is re‑enabled and other optimizations land. ([Python documentation][1])

---

## Further reading

-   **What’s New in Python 3.13: Free‑threaded CPython** (release notes). ([Python documentation][4])
-   **Python’s free‑threading HOWTO** (user‑facing behavior, limitations). ([Python documentation][1])
-   **C API Extension Support for Free‑Threading** (porting guidance, critical sections). ([Python documentation][7])
-   **PEP 703: Making the GIL Optional** (design rationale & mechanisms). ([Python Enhancement Proposals (PEPs)][3])
-   **PEP 684: Per‑Interpreter GIL** (historical and architectural groundwork). ([Python Enhancement Proposals (PEPs)][2])
-   **Free‑Threaded Python community guide & compatibility tracker.** ([py-free-threading.github.io][5])

---

### Epilogue

Free‑threading doesn’t undo the last three decades of Python design. It **rebalances** the trade‑off: single‑thread simplicity still matters, but we no longer have to sacrifice multi‑core parallelism when threads are the right tool. If you love understanding how languages work under the hood, 3.13 is a rare moment where user‑visible semantics and runtime internals took a big, coordinated step together—carefully, and with escape hatches—so we can write simpler, faster, _more parallel_ Python when we want to.

[1]: https://docs.python.org/3.13/howto/free-threading-python.html "Python experimental support for free threading — Python 3.13.9 documentation"
[2]: https://peps.python.org/pep-0684/?utm_source=chatgpt.com "PEP 684 – A Per-Interpreter GIL | peps.python.org"
[3]: https://peps.python.org/pep-0703/?utm_source=chatgpt.com "PEP 703 – Making the Global Interpreter Lock Optional in ..."
[4]: https://docs.python.org/3/whatsnew/3.13.html "What’s New In Python 3.13 — Python 3.14.0 documentation"
[5]: https://py-free-threading.github.io/installing-cpython/ "Installing Free-Threaded Python - Python Free-Threading Guide"
[6]: https://docs.python.org/3/howto/free-threading-python.html "Python support for free threading — Python 3.14.0 documentation"
[7]: https://docs.python.org/3/howto/free-threading-extensions.html "C API Extension Support for Free Threading — Python 3.14.0 documentation"
[8]: https://py-free-threading.github.io/tracking/ "Compatibility Status Tracking - Python Free-Threading Guide"
