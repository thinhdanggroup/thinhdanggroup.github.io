---
title: "Free-Threaded Python on a Real Workload"
description: "What a free-threading benchmark actually measures, why the easy comparison flatters it, and how to get the number your service's decision rests on."
tags:
    - Python
    - Performance
categories:
    - python
header:
    overlay_image: /assets/images/measuring-free-threaded-python/banner.webp
    overlay_filter: 0.5
    teaser: /assets/images/measuring-free-threaded-python/teaser.webp
toc: true
toc_sticky: true
---

You swap `python` for `python3.14t`, run the four-thread benchmark that has been sitting in the repo since the no-GIL argument started, and watch it finish in a fraction of the time. You ship it. Throughput on the actual service moves by a couple of percent, and p99 gets slightly worse.

Nothing malfunctioned. The benchmark measured exactly what you told it to measure. It just answered a question nobody was asking.

## There are three interpreters here, not two

Framing this as "GIL versus no GIL" hides a third configuration, and the third one is where the confusion lives. You can run:

- `python3.14` — the default build. GIL on, none of the free-threading machinery compiled in.
- `python3.14t -X gil=1` — the free-threaded build with the GIL turned back on.
- `python3.14t -X gil=0` — the free-threaded build doing what it was built for.

The `t` suffix is the convention: "The free-threaded Python executable will always have a `python3.14t` alias (for Python 3.14)". What you cannot assume is anything beyond that — "Whether `python`, `python3` and/or `python3.14` point at the free-threaded executable depends on the installation method used." Which is the first reason a benchmark should check what it is actually running rather than trust the name it was invoked by.

That middle configuration is not a curiosity. The runtime switch is documented and supported: "Free-threaded builds of CPython support optionally running with the GIL enabled at runtime using the environment variable `PYTHON_GIL` or the command-line option `-X gil`." The command-line docs spell out the values: "`-X gil=0,1` forces the GIL to be disabled or enabled, respectively. Setting to `0` is only available in builds configured with `--disable-gil`." Which is what makes it useful for bisecting a compatibility problem without rebuilding.

Three configurations give you three possible comparisons, and each answers a different question:

| Comparison | What it isolates | What it tells you |
| --- | --- | --- |
| `3.14` → `3.14t -X gil=1` | the free-threading tax | what you pay before a single thread scales |
| `3.14t -X gil=1` → `3.14t -X gil=0` | GIL removal alone | an upper bound on the parallel win |
| `3.14` → `3.14t -X gil=0` | both at once | the number your decision actually rests on |

The middle row is the cheapest of the three to set up — one binary, one flag, no second toolchain, no second virtualenv — which makes it the easy comparison to reach for. It is also the most flattering possible framing, because the baseline is an interpreter that pays the full cost of free-threading and is then forbidden from collecting any of the benefit. You are measuring against something deliberately hobbled.

The decision in front of you is the bottom row. Your production service does not currently run `python3.14t -X gil=1`.

## The tax got small, and that is the real news

Through 3.13 the honest advice was to stay away, and the release notes said so: "The free-threaded mode is experimental and work is ongoing to improve it: expect some bugs and a substantial single-threaded performance hit."

3.14 changed that arithmetic. "The performance penalty on single-threaded code in free-threaded mode is now roughly 5-10%, depending on the platform and C compiler used." The free-threading howto is more specific, and more useful, because it names the spread: "On the pyperformance benchmark suite, the average overhead ranges from about 1% on macOS aarch64 to 8% on x86-64 Linux systems."

A 1%-to-8% spread across platforms is itself the point. There is no single tax figure to quote at your team. There is a figure for your CPU architecture, your compiler, and your workload.

A large part of that came from one change, and the release notes are careful not to give it sole credit: "The specializing adaptive interpreter (PEP 659) is now enabled in free-threaded mode, which along with many other optimizations greatly improves its performance." The 3.13 free-threaded build ran with that optimization switched off.

That improvement is also what let the build shed the experimental label. PEP 779 set numeric entry criteria rather than vibes — "we propose 15% as a hard performance target" for single-threaded regression, and "We propose a target of 20% (geometric mean, as measured by pyperformance) for phase II" for memory. What the release notes then record, in a single line, is the outcome: "PEP 779: Free-threaded Python is officially supported".

Supported is not the same as default, and the PEP is careful about it: "Phase II would make the free-threaded build officially supported but still optional." Choosing the build is still your call, and still your risk.

So the tax is now single digits on most hardware. Which means whether free-threading wins is almost entirely a question about your workload rather than about CPython — and that is a question only your workload can answer.

## A harness that measures the right thing

```python
# bench.py — one script, run once per configuration.
import os
import sys
import sysconfig
import threading
import time


def actual_mode() -> str:
    """Which of the three configurations are we really in?"""
    # Coerce: the config var is absent on default builds, set to 1 on free-threaded ones.
    free_threaded = int(sysconfig.get_config_var("Py_GIL_DISABLED") or 0) == 1
    if not free_threaded:
        return "gil"
    # getattr guard: the function is a CPython implementation detail, not
    # guaranteed to exist in other Python implementations.
    gil_on = getattr(sys, "_is_gil_enabled", lambda: True)()
    return "ft-gil" if gil_on else "ft-nogil"


def cpu_work(iterations: int) -> int:
    total = 0
    for i in range(iterations):
        total += i * i % 7
    return total


def run(threads: int, total_iterations: int) -> float:
    # Fixed total work, split n ways: this measures scaling, not throughput
    # inflation from simply handing the machine more to do.
    per_thread = total_iterations // threads
    workers = [
        threading.Thread(target=cpu_work, args=(per_thread,))
        for _ in range(threads)
    ]
    start = time.perf_counter()
    for w in workers:
        w.start()
    for w in workers:
        w.join()
    return time.perf_counter() - start


if __name__ == "__main__":
    expected = os.environ["EXPECT"]
    got = actual_mode()
    if got != expected:
        raise SystemExit(f"refusing to benchmark: expected {expected}, running {got}")

    for n in (1, 2, 4, 8):
        print(f"{n:>2} threads  {run(n, 40_000_000):6.2f}s  [{got}]")
```

Run it three times, once per configuration:

```bash
EXPECT=gil      python3.14                bench.py
EXPECT=ft-gil   python3.14t -X gil=1      bench.py
EXPECT=ft-nogil python3.14t -X gil=0      bench.py
```

Two details in there matter more than the timing loop.

**The work is fixed and divided, not multiplied.** A benchmark that gives each thread its own full unit of work will report a rising number as you add threads even when nothing parallelizes, because you handed the machine more to do. Splitting a constant total is what turns the output into a scaling curve you can read.

**The run refuses to start in the wrong mode.** `sysconfig.get_config_var("Py_GIL_DISABLED")` is the documented way to ask about the build — "This is the recommended mechanism for decisions related to the build configuration" — and `sys._is_gil_enabled()` answers the separate question of what this process is doing right now: "The new `sys._is_gil_enabled()` function can be used to check whether the GIL is actually disabled in the running process." You need both, because the build and the runtime state can disagree.

## The failure that quietly invalidates the whole exercise

That mode assertion is not defensive padding. It guards against the single most likely way this measurement goes wrong: the GIL turning itself back on without you noticing.

"The GIL may also automatically be enabled when importing a C-API extension module that is not explicitly marked as supporting free threading. A warning will be printed in this case." The opt-in is on the extension author, not on you — "Extension modules need to explicitly indicate that they support running with the GIL disabled; otherwise importing the extension will raise a warning and enable the GIL at runtime" — and the docs are blunt that this is common in the wild: "Some third-party packages, in particular ones with an extension module, may not be ready for use in a free-threaded build, and will re-enable the GIL."

A warning on stderr, in a CI log nobody reads, is exactly how a "free-threaded" deployment ends up running with the GIL on for a quarter.

Which means the toy benchmark above is measuring the wrong process. Your service imports a database driver, a serializer, a metrics client, and forty transitive dependencies. Import that graph *before* you check the mode:

```python
import app.services  # the real import graph, not a synthetic workload

expected = os.environ["EXPECT"]
got = actual_mode()
if got != expected:
    raise SystemExit(f"refusing to benchmark: expected {expected}, running {got}")
```

If that assertion fires, you have learned something far more valuable than a timing number: you have found the dependency that would have silently capped your production deployment, months before you deployed it.

## Parallel is not the same as safe

One last thing the speedup number will not tell you. The docs describe the thread-safety situation carefully, and the caveat is the important half: "Built-in types like `dict`, `list`, and `set` use internal locks to protect against concurrent modifications in ways that behave similarly to the GIL. However, Python has not historically guaranteed specific behavior for concurrent modifications to these built-in types, so this should be treated as a description of the current implementation, not a guarantee of current or future behavior."

The recommendation that follows is unambiguous: "It's recommended to use the `threading.Lock` or other synchronization primitives instead of relying on the internal locks of built-in types, when possible."

The GIL never made your code thread-safe. It made a particular class of race narrow enough that a lot of code survived having one. Removing it does not introduce bugs; it changes the odds on bugs you already shipped, and it changes them on code paths your test suite runs single-threaded.

## What to do with this

Run the three-way comparison on your own service, with your own dependency graph imported, and read the bottom row of that table. If your workload is genuinely CPU-bound and genuinely parallel, a single-digit tax is cheap for real core utilization and the switch is worth costing out. If your service is I/O-bound — and most services calling themselves CPU-bound are waiting on something — you will pay the tax and collect nothing, because threads were already releasing the GIL on every socket read.

The build is supported now. That is a statement about CPython's readiness, not about yours.

## Further reading

- [Python support for free threading](https://docs.python.org/3/howto/free-threading-python.html) — the user-facing howto: detection, runtime switches, thread-safety caveats.
- [What's New in Python 3.14](https://docs.python.org/3/whatsnew/3.14.html) — the official-support announcement and the 5-10% figure.
- [What's New in Python 3.13](https://docs.python.org/3/whatsnew/3.13.html) — the experimental-mode framing this replaced.
- [PEP 779 – Criteria for supported status for free-threaded Python](https://peps.python.org/pep-0779/) — the numeric targets proposed for supported status.
- [C API Extension Support for Free Threading](https://docs.python.org/3/howto/free-threading-extensions.html) — how an extension opts in, and what happens when it does not.
- [Command-line `-X gil` and `PYTHON_GIL`](https://docs.python.org/3/using/cmdline.html) — the exact semantics of the runtime switch.
- [Running Python with the GIL Disabled](https://py-free-threading.github.io/running-gil-disabled/) — Quansight Labs' guide; the source for the `t`-suffix naming, which the CPython docs do not specify.
- [Breaking Down Python 3.13's Experimental Free-Threading Mode](/python313-free-threading/) — the 3.13-era background this post updates.
