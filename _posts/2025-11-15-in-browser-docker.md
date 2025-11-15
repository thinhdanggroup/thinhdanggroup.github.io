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
    overlay_image: /assets/images/in-browser-docker/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/in-browser-docker/banner.png
title: "Browser-Driven Infrastructure: How WebAssembly and In-Browser Docker Are Redefining Developer Environments"
tags:
    - in-browser docker
    - infrastructure
    - devx
---

Modern developer environments are moving into the browser. Not just editors and terminals—but whole stacks that used to require a VM, a container runtime, and a careful dance of installed dependencies. If you’ve tried a “Docker in the browser” demo lately, or spun up a full Node.js project without leaving a tab, you’ve tasted the future: lightweight, sandboxed, instantly shareable infrastructure.

This post unpacks **how** this is even possible. We’ll dig into WebAssembly (Wasm), WASI, OCI images, and the sleight-of-hand that lets a web page impersonate an operating system well enough to run serious workloads. Along the way we’ll build a mental model of the moving pieces, peek at a few code snippets, and finish with the trade-offs that matter if you’re building cloud IDEs or fleet-scale developer tooling.

---

## The Setup: Why the Browser, Why Now?

The browser offers three superpowers:

1. **Security**: hardened sandboxes and permission prompts by default.
2. **Distribution**: zero install, instant upgrades, link-to-share.
3. **Portability**: runs on everything, mobile included (sometimes!).

Historically, the browser lacked the one thing developer environments needed most: _a process sandbox with system-like capabilities._ We had JavaScript, and later asm.js, but the gap between “type some code” and “simulate a POSIX system with file system, sockets, and processes” was huge.

Two ingredients have changed the game:

-   **WebAssembly (Wasm)** is a safe, fast, portable bytecode that browsers can execute at near-native speeds. Importantly, Wasm isolates code and lets the host selectively expose capabilities—no ambient authority.
-   **WASI (WebAssembly System Interface)** is a spec for system-like calls (files, clocks, random, sockets, etc.). Think of it as _“POSIX-inspired capabilities for Wasm.”_ WASI is evolving, but even today it provides a path to run real programs without binding to a particular OS.

Between Wasm and WASI, a web page can host binaries compiled from C/C++/Rust/Go, give them a virtual filesystem, a clock, randomness, and controlled I/O, and keep them within a strict sandbox. Combine that with smart use of the browser APIs (Service Workers, Cache Storage, Web Streams, WebTransport/WebSockets), and you start to approach the power of a tiny OS.

---

## A Tale of Two Approaches

When people say “Docker in the browser,” they usually mean one of two architectures:

1. **Wasm-First Runtimes (WebContainers-style)**
   The “container” is actually a set of Wasm modules plus an emulated environment (filesystem, process model) crafted for the workload. Node.js in the browser is the canonical example: you don’t boot Linux; you load a Wasm build of the runtime and polyfill the bits it expects.

2. **OCI-Image-Aware Executors**
   The browser fetches an **OCI image** (the standard format Docker uses), reconstructs a filesystem by applying its tar layers, and then “runs” something _compatible_ with the image—often a Wasm build of the same app, or a Wasm shim that knows how to execute familiar tools. You’re not running a Linux kernel; you’re **interpreting the image** and executing compatible binaries inside a browser-backed sandbox.

Both avoid shipping a VM. Both depend on Wasm for speed and safety. The difference is philosophical: emulate a _runtime_ vs emulate a _container artifact_. In practice, many systems blend the two.

---

## Wasm and WASI: The Smallest Possible OS

Let’s anchor to a concrete example: a tiny Rust program compiled for WASI that writes a file and prints a directory listing.

```rust
// Cargo.toml
// [package]
// name = "wasi-demo"
// version = "0.1.0"
// edition = "2021"
//
// [dependencies]

// src/main.rs
use std::fs::{self, File};
use std::io::Write;

fn main() -> std::io::Result<()> {
    // In WASI, the program only sees directories the host "preopens"
    // (capability model). Think: "grant read/write to /workspace".
    File::create("hello.txt")?.write_all(b"hello, wasm!\n")?;
    for entry in fs::read_dir(".")? {
        let entry = entry?;
        println!("{}", entry.file_name().to_string_lossy());
    }
    Ok(())
}
```

Compile for WASI:

```bash
rustup target add wasm32-wasi
cargo build --target wasm32-wasi --release
# outputs target/wasm32-wasi/release/wasi-demo.wasm
```

This `.wasm` artifact has no ambient access to your machine. The host (browser or server runtime) must explicitly provide a filesystem “preopen” (a directory to mount), a stderr/stdout sink, and clock access. In the browser, a Wasm runtime glues this to the **Origin Private File System** (via the File System Access API) or an in-memory FS.

What’s powerful here isn’t the program; it’s the **security model**. You get POSIX-like primitives but behind a **capability wall**—you can’t `open("/etc/shadow")` unless the host gave you `/etc`.

> **Mini-summary:** WASI gives you portable system calls with capability-scoped access. The browser is the host that decides which capabilities to expose.

---

## How Browsers Emulate “Process” and “Filesystem”

Real Linux provides syscalls. Browsers don’t. To bridge the gap, in-browser runtimes assemble a small stack:

-   **Wasm runtime** (in JS or WASM): loads and executes modules, maps WASI calls to host functions.
-   **Virtual filesystem**: usually an in-memory tree with adapters for IndexedDB, OPFS (Origin Private File System), and HTTP-backed lazy files.
-   **Process emulation**: one Wasm instance ≈ one “process.” For “fork/exec,” systems use copy-on-write snapshots, multi-instance orchestration, or extend WASI (e.g., WASIX) to simulate POSIX semantics.
-   **Networking**: there’s no raw TCP in the browser. Runtimes tunnel through **WebSocket**/**WebTransport** to a proxy, or offer a loopback device implemented in JS.

A simplified adapter for filesystem syscalls might look like this:

```ts
// Very simplified WASI host bindings for file I/O.
import { WASI } from "@wasmer/wasi"; // conceptually; could be any WASI lib

class BrowserFS {
    #files = new Map<string, Uint8Array>();

    readFile(path: string): Uint8Array {
        const buf = this.#files.get(path);
        if (!buf) throw new Error("ENOENT");
        return buf;
    }

    writeFile(path: string, data: Uint8Array) {
        this.#files.set(path, data);
    }

    readdir(path: string): string[] {
        // pretend flat filesystem
        return Array.from(this.#files.keys()).filter((p) => p.startsWith(path));
    }
}

const vfs = new BrowserFS();

const wasi = new WASI({
    bindings: {
        // map WASI fd_read/fd_write to JS functions over vfs
        fs: {
            readFile: (pathPtr, pathLen, bufPtr, bufLen) => {
                /* ... */
            },
            writeFile: (pathPtr, pathLen, bufPtr, bufLen) => {
                /* ... */
            },
            readdir: (pathPtr, pathLen, outPtr) => {
                /* ... */
            },
        },
        // clocks, random, etc...
    },
    preopenDirectories: { "/": vfs }, // capability grant
});

// Instantiate your .wasm with these host functions.
```

It’s not a full POSIX implementation (and you wouldn’t write it by hand), but the idea is simple: **translate** WASI calls to browser primitives.

---

## Where OCI Images Fit In

Containers are more than processes; they’re **artifacts**: an image with layers, a config, and metadata. Even if we can’t boot a Linux kernel in a tab, we can still:

1. **Pull** an image from a registry (it’s just HTTP with JSON manifests and tar layers).
2. **Apply** the layers to assemble a root filesystem.
3. **Execute** an entrypoint—_compatible with our environment_.

Here’s what a minimal “pull and materialize” looks like in pseudo-JavaScript. It leaves out auth and digests, but captures the flow:

```ts
// Step 1: Fetch image manifest and layers.
async function fetchOCIImage(ref: {
    registry: string;
    repo: string;
    tag: string;
}) {
    const base = `https://${ref.registry}/v2/${ref.repo}`;
    const token = await getBearerToken(ref); // standard registry auth flow
    const headers = { Authorization: `Bearer ${token}` };

    const manifest = await (
        await fetch(`${base}/manifests/${ref.tag}`, { headers })
    ).json();
    const layers = manifest.layers.filter((l: any) =>
        l.mediaType.includes("tar")
    );

    // Step 2: Apply tar layers into a virtual filesystem.
    for (const layer of layers) {
        const resp = await fetch(`${base}/blobs/${layer.digest}`, { headers });
        const stream = resp.body; // Web Streams API
        await untarIntoVFS(stream); // your tar reader writes into vfs
    }

    const configDigest = manifest.config.digest;
    const config = await (
        await fetch(`${base}/blobs/${configDigest}`, { headers })
    ).json();

    return { config }; // contains entrypoint/cmd/env/workingDir
}

// Untar to your vfs (sketch).
async function untarIntoVFS(stream: ReadableStream<Uint8Array>) {
    const reader = stream.getReader();
    let buffer = new Uint8Array(0);
    while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer = concat(buffer, value);
        while (hasCompleteTarEntry(buffer)) {
            const { header, file, rest } = takeTarEntry(buffer);
            buffer = rest;
            if (header.typeflag === "0" /* file */) {
                vfs.writeFile(`/${header.name}`, file);
            } else if (header.typeflag === "5" /* dir */) {
                vfs.mkdirp(`/${header.name}`);
            } else if (header.typeflag === "2" /* symlink */) {
                vfs.symlink(`/${header.name}`, header.linkname);
            }
        }
    }
}
```

At the end of this, you have a container’s root filesystem in memory (or OPFS). The missing piece is _how to run the entrypoint_. In a real Linux container, that’s an ELF binary using Linux syscalls. In the browser you typically choose one of:

-   **Wasm-native entrypoints**: the image is built for WASI instead of Linux, so the entrypoint is `program.wasm`. (There’s ongoing work to store Wasm modules directly as OCI artifacts.)
-   **Runtime shims**: you “exec” a Wasm runtime that can interpret scripts (Node, Python) using Wasm builds of those runtimes.
-   **User-space emulation**: advanced systems map Linux-style calls onto WASI/WASIX. This is bleeding-edge and comes with trade-offs.

> **Mini-summary:** The browser can understand container _artifacts_ (OCI) and hydrate filesystems. Executing the entrypoint requires compatibility with the browser’s capability set—usually via Wasm.

---

## Networking: Sockets Without Sockets

Containers expect TCP/IP. Browsers don’t expose raw sockets (for good reasons). How do browser-hosted environments “talk to the internet”?

-   **HTTP(S)**: direct `fetch` is easy—but only to HTTP(S) endpoints, with CORS constraints.
-   **WebSocket/WebTransport Proxies**: to simulate outbound TCP, environments proxy socket semantics through a service that multiplexes many virtual streams over a single browser-friendly connection. The in-browser runtime implements `connect()`, `send()`, `recv()` against that tunnel.
-   **Localhost**: some environments create an in-tab loopback “network” so `localhost:3000` is actually a JS implementation of a TCP stack feeding your dev server. It’s smoke and mirrors—but very effective smoke.

A tiny sketch of a socket shim:

```ts
class Socket {
    #stream: WebSocket;

    constructor() {
        this.#stream = new WebSocket("wss://tcp-proxy.example/socket");
    }

    async connect(host: string, port: number) {
        // Ask the proxy to open a TCP connection on our behalf.
        this.#stream.send(JSON.stringify({ op: "connect", host, port }));
        // Proxy replies with success/error; we resolve or throw.
    }

    send(data: Uint8Array) {
        this.#stream.send(data);
    }

    async recv(): Promise<Uint8Array> {
        return new Promise((resolve) => {
            this.#stream.onmessage = (ev) => resolve(new Uint8Array(ev.data));
        });
    }

    close() {
        this.#stream.close();
    }
}
```

The WASI `sock_*` calls get wired to this shim. It’s not “real” TCP in the tab; it’s a capability-mediated pipe to something that is.

---

## Process Model: “fork,” Signals, and the Reality Check

POSIX expects `fork`, `exec`, `waitpid`, signals, and file descriptor inheritance. WebAssembly 1.0 gave us _none_ of these. Projects have taken three paths:

1. **Avoid fork/exec**: design the toolchain so processes are cheap (one Wasm module per “process”) and use message passing.
2. **WASI extensions**: proposals (and community extensions like WASIX) add process creation, sockets, and more. These work in server runtimes and can be polyfilled in browsers with varying fidelity.
3. **Snapshot-and-spawn**: some systems freeze a Wasm instance’s memory and table, then copy it to create “children,” faking `fork` behavior for typical use cases (think `spawn` with inherited stdio and environment).

The takeaway is practical: **most dev workflows don’t need perfect POSIX**. If your environment runs Node, a package manager, a build tool, a test runner, and a dev server, you’re 90% there. The final 10% (ptrace, low-level signals, kernel features) remains out of scope for browsers by design.

---

## Putting It Together: A Browser-Native “Container Run”

Let’s outline a flow that “runs” a containerized app in a tab:

1. **Boot**: load the page; a Service Worker preps caches and a Wasm runtime.
2. **Fetch**: pull an OCI image, apply its layers into OPFS.
3. **Resolve entrypoint**: if it’s a Wasm module (`*.wasm`) or a script (Node/Python) with a Wasm runtime available, proceed; else show a compatibility error.
4. **Mounts**: create bind-mounts from `/workspace` to a project folder in OPFS; set env vars.
5. **Start**: instantiate the Wasm runtime with WASI bindings (stdio, clock, random, fs, sockets). Hook stdio to an on-page terminal.
6. **Network**: wire sockets to a WebSocket/WebTransport proxy; expose loopback to the dev server.
7. **Persistence**: intercept writes to cache layers; layer filesystem changes so you can create “commits” back into OCI-like diffs if needed.
8. **Share**: serialize the workspace to an opaque URL or push the filesystem to a remote store; collaborators click a link and land in the exact state.

If that sounds like a properly engineered container runtime, it is—just implemented with browser primitives.

---

## Performance: Start Fast, Stay Fast

Browser-driven infra lives or dies on perceived performance. Three tactics matter:

-   **Eager streaming & progressive hydration**: start execution before the whole image is present. You can stream a tar layer and materialize only the files touched by the entrypoint. The Web Streams API makes this natural.
-   **Dedup across tabs and sessions**: caches (HTTP, Service Worker, OPFS) are your friend. Pin common layers (base images, package registries) across projects.
-   **Snapshotting**: if your runtime supports it, snapshot a warm process to disk and resume instantly. This is how some systems achieve “project opens in ~1s.”

It’s not universally faster than local containers—especially for CPU-heavy builds—but the **time-to-first-keystroke** and **zero install** often win.

---

## Security: A Different Threat Model (Mostly Better)

Running untrusted code locally means it can read your files, open sockets, and sniff your network. Running untrusted code in a tab means:

-   It lives inside the **web sandbox** (same-origin, CORS, CSP).
-   It only sees **capabilities you granted** (VFS mounts, proxies).
-   It cannot access your host filesystem or kernel.
-   It still needs careful **supply-chain hygiene** (images, modules, and registries can be compromised).

One sharp edge: **proxy services** for sockets effectively act as ambient network authority. Treat them like you’d treat a VPN egress or NAT gateway: audit, authenticate, and log.

---

## What Cloud IDEs Gain (and What They Don’t)

**Gains:**

-   **Zero-install onboarding**: a link boots a full environment.
-   **Deterministic sandboxes**: fewer “works on my machine” bugs.
-   **Cost shift to clients**: less server spend for ephemeral dev.
-   **Offline-ish**: with pre-cached layers and registries, you can do serious work on a plane.
-   **Safer PR previews**: run untrusted contributor code in the browser.

**Trade-offs:**

-   **Limited kernel features**: anything that needs raw devices, privileged syscalls, or ptrace is out.
-   **Network constraints**: CORS, proxies, and corporate firewalls complicate things.
-   **Performance ceilings**: heavy native toolchains (e.g., complex C++ compilers) may lag without careful tuning and caching.
-   **State management**: syncing large workspaces between local, browser, and remote gets tricky.

---

## A Walkthrough: Building a Browser-Side Layered Filesystem

To make this concrete, here’s a minimal layered filesystem model you can adapt. We’ll keep it high level and readable.

```ts
type File = { data: Uint8Array; mode: number; mtime: number; symlink?: string };

class Layer {
    files = new Map<string, File>();
    whiteouts = new Set<string>(); // OCI whiteouts delete lower files
}

class UnionFS {
    constructor(private layers: Layer[]) {}

    stat(path: string): File | undefined {
        for (let i = this.layers.length - 1; i >= 0; i--) {
            const l = this.layers[i];
            if (l.whiteouts.has(path)) return undefined;
            const f = l.files.get(path);
            if (f) return f;
        }
        return undefined;
    }

    readFile(path: string): Uint8Array {
        const f = this.stat(path);
        if (!f) throw new Error("ENOENT");
        if (f.symlink) return this.readFile(f.symlink);
        return f.data;
    }

    // Writes always go to the top layer
    writeFile(path: string, data: Uint8Array, mode = 0o644) {
        const top = this.layers[this.layers.length - 1];
        top.whiteouts.delete(path);
        top.files.set(path, { data, mode, mtime: Date.now() });
    }

    unlink(path: string) {
        const top = this.layers[this.layers.length - 1];
        top.whiteouts.add(path);
        top.files.delete(path);
    }

    list(prefix: string): string[] {
        const out = new Set<string>();
        for (let i = 0; i < this.layers.length; i++) {
            for (const p of this.layers[i].files.keys()) {
                if (p.startsWith(prefix)) out.add(p);
            }
            for (const w of this.layers[i].whiteouts) {
                if (w.startsWith(prefix)) out.delete(w);
            }
        }
        return Array.from(out);
    }
}

// Usage:
// base layer ← from OCI
// app layer  ← from OCI
// work layer ← mutable (user edits)
const base = new Layer();
const app = new Layer();
const work = new Layer();
const fs = new UnionFS([base, app, work]);

// write a file (goes to work layer)
fs.writeFile(
    "/workspace/main.js",
    new TextEncoder().encode("console.log('hi')")
);
```

This is enough to:

-   Apply OCI tar layers into `Layer` objects.
-   Overlay mutable state on top.
-   Export diffs from `work` as a new tar layer for sharing/snapshotting.

Pair it with OPFS persistence and you’ve got a resilient on-device cache.

---

## Debugging the Illusion

When something breaks in a browser-hosted environment, the failure modes differ from Linux:

-   **EACCES where POSIX would succeed**: you forgot to preopen or mount a directory in WASI.
-   **Networking flakiness**: your WebSocket proxy drops under load; add backpressure and retry.
-   **CORS**: your image registry or package mirror needs CORS headers for `fetch` to work in the browser.
-   **Clock or entropy**: cryptographic libraries may assume `getrandom`; ensure WASI random is wired to `crypto.getRandomValues`.

Instrumentation tips:

-   Expose WASI syscalls to a developer console log (behind a flag).
-   Add a “sysfs-like” page that lists mounts, env vars, and open file descriptors.
-   Use the Performance API to measure layer apply times and startup latency.

---

## The Emerging Convergence: Containers + Wasm

On servers, the container ecosystem is adding first-class support for Wasm modules as OCI artifacts and as runtimes behind **containerd**. In browsers, we’re going the other direction: treating OCI images as a **distribution format** for code that executes via Wasm.

This convergence suggests a future where:

-   Teams publish **dual-target images**: Linux for servers, WASI for browsers/edge/devtools.
-   Registries serve the same tags to both worlds.
-   Tooling can **promote** a browser-side snapshot (your in-tab work layer) back into an image for CI—without leaving the page.

It’s not fully here yet, but the pieces are aligning.

---

## Practical Guidance for Cloud IDE Builders

1. **Choose your baseline:**
   Start with a Wasm-first model (e.g., Node in Wasm, Python via Pyodide) and layer in OCI image support for assets and filesystem hydration. It’s the quickest path to “wow.”

2. **Lean into capability security:**
   Don’t mount everything. Make the default sandbox tiny and ask for explicit grants (e.g., “Allow access to this project folder?”).

3. **Proxy well:**
   Build or adopt a robust WebSocket/WebTransport TCP proxy with auth, quota, and observability. It’s your network lifeline.

4. **Cache aggressively:**
   Bake a background prefetch of common bases into your Service Worker. Measure cache hit rate like you would measure CDN hit rate.

5. **Offer snapshots:**
   Snap/resume dev servers and build caches. “Open in 1–2s” is a signature feature users notice.

6. **Be honest about compat:**
   Publish a compatibility matrix. If something needs kernel features you won’t emulate, say so early.

7. **Make sharing delightful:**
   URLs that encode workspace state (or point to a durable store) turn “it compiles on my machine” into “it compiles in this link.”

---

## Historical Context (Because it’s Fun)

-   **Native Client (NaCl) and PNaCl** tried to run native code safely in Chrome a decade ago; the web community wanted a standards-based path.
-   **asm.js** proved that JS engines could JIT a subset of JS to near-native speed.
-   **WebAssembly** standardized the idea and decoupled it from JS syntax.
-   **WASI** is completing the picture: safe, portable system interfaces that run anywhere—browsers, servers, edge.

We’ve come a long way from “minified JS all the way down” to “ship a compiler toolchain in your tab.”

---

## Limitations and Honest Edges

Let’s list the sharp corners you will hit:

-   **No kernel, no cgroups**: you can simulate resource limits but not enforce them with kernel authority.
-   **File watching**: chokidar-style watch works, but inotify semantics aren’t available. Expect occasional differences.
-   **Pathological builds**: giant C++ link steps are slow without native toolchains. Consider remote cache or split compilation.
-   **Binary compatibility**: ELF binaries built for Linux do not run in the browser. You’ll need WASI builds, language runtimes in Wasm, or emulation layers with overhead.

These aren’t deal-breakers for a huge class of dev workflows (web, Node, Python, Rust, docs, tests, CLIs). They are worth naming early for power users.

---

## Key Takeaways

-   **Browser-driven infrastructure** is real and useful: with Wasm + WASI + smart shims, a web page can execute serious developer workloads safely and fast.
-   **“Docker in the browser”** usually means _OCI-aware filesystems plus Wasm-compatible entrypoints_, not a Linux kernel in a tab.
-   **Security improves** by default: capability-scoped filesystems, proxied networking, and a hardened sandbox beat “run this on your laptop.”
-   **Performance is competitive** when you stream, cache, and snapshot wisely—especially for iterative dev loops.
-   **Convergence is coming**: the same image references and registries will increasingly serve both servers and browsers with appropriate targets.

---

## Further Reading & Exploration

-   WebAssembly core concepts and the WASI specification (capability-oriented design).
-   How OCI images are structured: manifests, layers, media types, and digests.
-   Building Service Worker–backed caches for large binary artifacts.
-   Web Streams API for progressive layer hydration and tar parsing.
-   WASI extensions (sockets, process model) and community efforts like WASIX.
-   Patterns for TCP-over-WebSocket/WebTransport proxying, backpressure, and auth.
-   Case studies of browser-hosted Node/Python/Rust toolchains and their compatibility profiles.

If you’re building a cloud IDE or you want to make your dev tools runnable anywhere, the browser is no longer a toy runtime—it’s a **portable, secure compute fabric**. The question isn’t whether we can run containers in the browser; it’s **which parts of the container experience we bring over on purpose**. The rest, as always, is good product design and careful engineering.
