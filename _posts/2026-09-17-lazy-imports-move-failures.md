---
title: "Python 3.15 Lazy Imports Move Your Failures Into The Request Path"
description: "PEP 810 defers import cost — and with it every ImportError and import-time side effect. What shipped in 3.15, what quietly didn't, and how to keep failing fast."
tags:
    - Python
    - Performance
categories:
    - python
header:
    overlay_image: /assets/images/lazy-imports-move-failures/banner.webp
    overlay_filter: 0.5
    teaser: /assets/images/lazy-imports-move-failures/teaser.webp
toc: true
toc_sticky: true
---

Your deploy goes green. The readiness probe is happy and the pod has been up for ninety
seconds. Then the first real checkout request arrives and returns a 500, with an
`ImportError` in the traceback for a dependency that was in your lockfile the whole time.

The service started cleanly because it never imported that dependency. Someone added
one word to a line at the top of a file, and the import that used to fail at boot now
fails on whichever request happens to touch it first.

That word is `lazy`, and it lands in Python 3.15 — due
[2026-10-01](https://peps.python.org/pep-0790/) — via
[PEP 810](https://peps.python.org/pep-0810/), which the steering council accepted
unanimously in November 2025. The performance case is real: the PEP claims lazy imports
"can reduce startup time by 50-70% in practice" and that "memory savings of 30-40% have
been observed in real workloads." But `lazy` defers more than cost. It defers every
consequence your import statement used to have, and those have to happen somewhere.

## What `lazy` actually defers

`lazy` is a soft keyword placed in front of a module-level import:

```python
lazy import boto3
lazy from myapp.plugins import registry
```

The module is not loaded when the interpreter executes that line. As the PEP puts it,
"a lazy proxy object is created and bound to the name. The actual module is loaded on
first use of that name." That loading step is called **reification**, and until it
happens the module is not in `sys.modules` at all.

The `from` form has a wrinkle worth internalizing. Each imported name gets its own
proxy, and per the language reference, "the first access to any of these names triggers
loading of the entire module and resolves only that specific name to its actual value.
Other names remain as lazy proxies until they are accessed." So one name resolving
tells you nothing about the others: you pay the load cost once, but keep a scattering
of unresolved proxies in your globals.

Two details save you debugging time later. Reification triggers on *accessing* the
name, so `globals()` and a module's `__dict__` do not collapse the proxies. And it is
thread-safe: the PEP specifies it "follows the existing import-lock discipline," with
one thread performing the import and atomically rebinding the global, and adds that
lazy imports "have no special considerations for free-threading."

Laziness is local. It "does not cascade recursively into other imports" —
marking `boto3` lazy does nothing to the forty modules `boto3` itself imports once it
finally loads. You moved a cliff, you did not flatten it.

## The failure surface moves with the cost

The error timing is stated plainly in the docs: "If an error occurs during module
loading (such as `ImportError` or `SyntaxError`), it is raised at the point where the
lazy import is first used, not at the import statement itself."

Read that as an operations statement rather than a language one. A missing wheel, an
import-time `SyntaxError` in a vendored module — both used to kill the process before it
could accept traffic, which is the single most useful thing a startup failure can do.
Now the process starts, passes its probes, joins the load balancer pool, and converts a
deploy-time crash into a runtime error rate.

It gets sharper. PEP 810 specifies that "if reification fails (e.g., due to an
`ImportError`), the lazy object is *not* reified or replaced. Subsequent uses of the
lazy object will re-try the reification." A failed eager import is one loud death. A
failed lazy import is the same exception on every single request that reaches that code
path, forever, with a healthy-looking process underneath it. Worth verifying against
your own build, incidentally — the 3.15 language reference describes the error timing
but is silent on retry.

Side effects move too, and this is where it stops being about errors. The PEP is
explicit that "side effects are deferred until first use" and warns that "the most
common reliance on import side effects is the registry pattern, where population of
some external registry happens implicitly during the importing of modules." If a module
exists to run a `@register` decorator at import time, a `lazy import` of it means the
registration simply never happens until something touches the name — and if nothing
ever touches the name, because the whole point was the side effect, the registration
never happens at all. No error, no traceback, just a plugin that isn't there.

The restriction that bites hardest in practice:

```python
# Python 3.14 and earlier: the optional-dependency dance
try:
    import orjson as json_impl
except ImportError:
    import json as json_impl

# Python 3.15: this is a SyntaxError, not a slow import
try:
    lazy import orjson as json_impl
except ImportError:
    import json as json_impl
```

"Lazy imports are only permitted at module scope. Using `lazy` inside a function, class
body, or `try`/`except`/`finally` block raises a `SyntaxError`." Star imports and
`__future__` imports are out too. Which means the heavy optional dependencies you most
want to defer — the ones already wrapped in a `try` precisely because they're optional —
are exactly the ones this syntax refuses to defer. Alyssa Coghlan named the underlying
tradeoff during the discussion: first-use error timing "rules out using lazy imports for
cheap existence checking."

## The off switch that didn't ship

Here is the part you will not find in the release summaries. PEP 810's specification
describes three global modes: `"normal"`, `"all"`, and `"none"` — the last one defined
as "No imports are lazy, even those explicitly marked with `lazy` keyword."

The shipped documentation describes two. `sys.set_lazy_imports()` in the 3.15 `sys`
docs: "The *mode* parameter must be one of the following strings: `"normal"` [...]
`"all"`." The command-line flag: "`-X lazy_imports=all,normal`." The environment
variable: "Accepts two values." No `none`, anywhere.

LWN covered the argument in March 2026. The flag was meant to serve pip, which has
"always promised not to run any of the code in a wheel at *install* time" — and
latency-sensitive programs that didn't want a surprise import pause. The objection that
dominated was that libraries using lazy imports to manage circular dependencies could
fail under it, making the flag "unusable anywhere outside the standard library," and
that authors would avoid the new syntax rather than risk it. One developer: "I'm
reluctant to port existing forms of deferred imports...knowing that I would be slowing
down or breaking anyone who uses `-X lazy_imports=none`."

That article closed undecided — "It is not clear where things go from here" — and what
shipped six months later has two modes.

The consequence for you is concrete and asymmetric. `-X lazy_imports=all` lets you make
your entire dependency tree lazy in one flag. Nothing lets you make it eager again. When
a library ships `lazy import` and it misbehaves in your process, you cannot switch it
off from the outside — you patch, vendor, or pin.

## Keeping fail-fast on purpose

Two mechanisms, both already in 3.15.

The filter is the one that matters if you're tempted by `"all"`. Adam Turner warned
during the discussion that the global mode could become a "hidden secret hack" for
performance, burying library maintainers in bug reports from configurations they never
supported. The filter is how you take the win without exporting it:

```python
import sys

HEAVY = frozenset({"boto3", "pandas", "torch"})

def our_code_only(importing_module: str, imported_module: str,
                  fromlist: tuple[str, ...] | None) -> bool:
    """Return True to allow laziness, False to force an eager import.

    Our own modules may defer the known-heavy dependencies. Every other
    import in the process — including every import our dependencies make
    internally — stays eager.
    """
    return importing_module.startswith("myapp.") and imported_module in HEAVY

sys.set_lazy_imports_filter(our_code_only)
sys.set_lazy_imports("all")
```

The signature is exactly as documented: `importing_module` is the module doing the
import, `imported_module` is the resolved target, and `fromlist` is the tuple of names
for a `from ... import` or `None` otherwise. Note that the `sys` docs explicitly tell
library authors to keep away from `set_lazy_imports()`: it "affects the runtime execution
of applications," which is not a library's call to make.

The second mechanism is a boot-time preflight — the thing that gives you back the crash
you gave up:

```python
# preflight.py — run this from your entrypoint, before the server binds a port.
import importlib

CRITICAL = ("boto3", "orjson", "myapp.plugins")

def preflight() -> None:
    """Resolve deferred dependencies while a failure is still a startup failure."""
    for name in CRITICAL:
        importlib.import_module(name)
```

This works because "dynamic import APIs remain eager and unchanged: `__import__()` and
`importlib.import_module()`" — no `lazy` binding and no `-X lazy_imports=all` touches
them. An unimportable dependency raises here, in the process's first second, instead of
in a request handler. It also warms `sys.modules`, so the later proxy resolution is a dict
lookup rather than a disk walk.

For diagnostics there is `sys.lazy_modules`, a set of module names "lazily imported
[...] but not yet loaded" — fine for a startup log line, but the docs warn that
"consumers are expected to verify each entry's status," and today it can also hold
attribute names like `"pathlib.Path"`.

## Key takeaways

- `lazy` defers loading to first *name access*, which moves `ImportError`,
  `SyntaxError`, and every import-time side effect from startup into whatever code path
  gets there first.
- The registry pattern is the silent failure: a deferred side effect that nothing ever
  triggers produces no error at all.
- `try: import x except ImportError:` cannot be made lazy — it's a `SyntaxError` — so
  your heaviest optional dependencies are the least deferrable ones.
- PEP 810 specified a `none` mode that disables all laziness. It is not in 3.15. You can
  globally enable laziness across your dependency tree; you cannot globally disable it.
- Scope `"all"` to your own modules with `sys.set_lazy_imports_filter()`, and use an
  eager `importlib.import_module` preflight to turn deferred failures back into
  startup failures.

Read the shipped documentation, not the PEP. On this feature they already disagree in
two places, and the one that governs your process is the one in `docs.python.org/3.15`.

## Further reading

- [PEP 810 — Explicit lazy imports](https://peps.python.org/pep-0810/)
- [PEP 790 — Python 3.15 release schedule](https://peps.python.org/pep-0790/)
- [What's New In Python 3.15](https://docs.python.org/3.15/whatsnew/3.15.html)
- [Python 3.15 language reference: the `import` statement](https://docs.python.org/3.15/reference/simple_stmts.html)
- [`sys` — lazy import APIs in Python 3.15](https://docs.python.org/3.15/library/sys.html)
- [Python command line and environment variables (3.15)](https://docs.python.org/3.15/using/cmdline.html)
- [LWN: Explicit lazy imports for Python](https://lwn.net/Articles/1041120/)
- [LWN: Python steering council accepts lazy imports](https://lwn.net/Articles/1044844/)
- [LWN: Disabling Python's lazy imports from the command line](https://lwn.net/Articles/1061112/)
