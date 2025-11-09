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
    overlay_image: /assets/images/realtime-developer-sandbox/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/realtime-developer-sandbox/banner.png
title: "Building Real-Time Developer Sandboxes: A Deep Dive into Browser-Based Docker Terminals with WebSockets"
tags:
    - Real-Time
    - JavaScript
    - WebSocket
---

Cloud IDEs have gone from “neat hack” to “real tools.” You type in a browser, a container compiles your code somewhere far away, and the feedback loop _feels_ local. Behind this magic is an unglamorous but fascinating subsystem: a low-latency, secure terminal stream from your browser to a Linux shell inside a container.

In this post, we’ll build that core: a browser-based terminal connected to a Docker container over WebSockets using Node.js and Express. We’ll go step-by-step—from architecture and protocol choices, to container hardening and backpressure—ending with a reference implementation you can extend.

> Audience: general programmers comfortable with Node.js, Docker, and basic web architecture.
> Goal: understand the moving parts well enough to build or review a production-grade browser↔container terminal.

---

## Table of Contents

1. Motivation: why terminals and why now
2. Architecture: one hop, no magic
3. The transport: WebSockets, binary frames, and backpressure
4. Spawning containers safely: limits, users, and policies
5. Wiring it up with Node.js, Express, `ws`, and Dockerode
6. The browser side: xterm.js, resize events, and keystroke latency
7. Authentication & authorization: short-lived tokens and origin checks
8. Lifecycle & cleanup: from cold starts to idle reap
9. Performance tuning: cutting tail latency
10. Hardening beyond Docker: gVisor/Kata/Firecracker
11. Observability & auditing
12. Summary & further reading

---

## 1) Motivation: why terminals and why now

Most interactive dev tools boil down to “run a command, show the output.” Editors, REPLs, test runners, package managers—these are terminal workloads. If you can ship a fast, safe terminal in the browser, you’ve built the foundation for:

-   One-click sandboxes for docs and tutorials
-   Zero-install onboarding for new engineers
-   Disposable environments for PR reviews
-   Classroom and interview coding sessions

The catch? You’re now operating a multi-tenant compute service where strangers execute arbitrary code. Low latency meets high paranoia. Fun!

---

## 2) Architecture: one hop, no magic

At a high level:

```
+------------+        wss://        +----------------+      /var/run/docker.sock
|  Browser   | <-------------------> | Node + Express | <------------------------+
|  xterm.js  |     WebSocket (TLS)   |  ws + Docker   |                          |
+------------+                       +----------------+                          |
                                                                              +--v------+
                                                                              | Docker  |
                                                                              | Engine  |
                                                                              +---------+
```

Key design decisions:

-   **Single hop**: The Node server that terminates the WebSocket should sit on the same host (or very close) as the Docker daemon. Every extra network hop adds jitter.
-   **Binary end-to-end**: Avoid base64. Send keystrokes and terminal bytes as binary frames.
-   **TTY semantics**: Allocate a PTY so line buffering and job control behave like a real terminal.
-   **Per-session isolation**: One ephemeral container per user session. Burn it down on disconnect/idle.

---

## 3) The transport: WebSockets, binary frames, and backpressure

Why WebSockets? You need full-duplex, low-overhead streaming that survives proxies. HTTP/2 streams are possible, but WebSockets are ubiquitous and well-supported.

A few ground rules that make terminals “feel” instant:

-   **Disable per-message deflate** (`perMessageDeflate: false`). Compression adds CPU latency and hurts interactive traffic (lots of tiny frames).
-   **Use binary frames**. Set `ws.binaryType = "arraybuffer"` in the browser and send `Uint8Array` both ways.
-   **Implement backpressure**. When the browser tab stutters or the network buffers, don’t keep shoveling bytes—pause the Docker stream and resume later.
-   **Keep-alives**. Use `ping/pong` to detect dead connections and reap containers.

We’ll implement all of the above shortly.

---

## 4) Spawning containers safely: limits, users, and policies

Container escapes are rare but not hypothetical. Assume hostile code. Harden aggressively:

-   **Non-root user** inside the container. Avoid `root`. Use user namespace remapping or `--user` to run as a low-privileged UID/GID.
-   **Drop capabilities**: `--cap-drop=ALL` and add back only what’s needed (often nothing).
-   **No new privileges**: `--security-opt no-new-privileges`.
-   **Restrictive seccomp/AppArmor**: Use Docker’s default seccomp or a custom policy; enable AppArmor/SELinux profiles where available.
-   **Resource limits**: `--cpus`, `--memory`, `--pids-limit`, `--ulimit nofile`, `--kernel-memory` (if applicable).
-   **Filesystem**: Prefer a **read-only root** with a **tmpfs** for `/tmp` and a dedicated workspace volume if you need persistence. For ephemeral sandboxes, make everything disposable.
-   **Networking**: Default-deny egress or at least restrict (e.g., internal metadata endpoints), and consider disabling IPv6 if you don’t monitor it.
-   **No docker.sock exposure**: Only your trusted Node process talks to the Docker API over the Unix socket.

We’ll encode much of this via Dockerode’s `HostConfig`.

---

## 5) Server wiring: Node.js, Express, `ws`, and Dockerode

Let’s build a minimal but production-shaped server. It will:

1. Authenticate the WebSocket upgrade with a **short-lived JWT**.
2. Start a **bounded** Docker container with a TTY.
3. **Attach** the client to the container’s stdin/stdout as a binary stream.
4. Handle **resize**, **keep-alive**, **backpressure**, and **cleanup**.

### Dependencies

```bash
npm i express ws dockerode jsonwebtoken zod
```

### `server.js`

```js
// server.js
"use strict";
const http = require("http");
const express = require("express");
const WebSocket = require("ws");
const Docker = require("dockerode");
const jwt = require("jsonwebtoken");
const { z } = require("zod");

const docker = new Docker({ socketPath: "/var/run/docker.sock" });
const app = express();

const JWT_SECRET = process.env.JWT_SECRET || "dev-please-override";
const IMAGE = process.env.SANDBOX_IMAGE || "node:20-alpine";
const IDLE_MS = parseInt(process.env.IDLE_MS || "600000", 10); // 10 mins
const MAX_WS_BUFFER = 1 * 1024 * 1024; // 1 MB

// Health endpoint for probes
app.get("/healthz", (_, res) => res.status(200).send("ok"));

const server = http.createServer(app);
const wss = new WebSocket.Server({
    noServer: true,
    path: "/term",
    clientTracking: false,
    perMessageDeflate: false,
});

// Verify JWT on upgrade
server.on("upgrade", async (req, socket, head) => {
    try {
        const url = new URL(req.url, "http://internal");
        const token = url.searchParams.get("token");
        if (!token) throw new Error("missing token");

        const payload = jwt.verify(token, JWT_SECRET); // throws on invalid
        // Optional: origin check
        const origin = req.headers.origin || "";
        if (!/^https?:\/\/(localhost(:\d+)?|yourdomain\.com)$/.test(origin)) {
            throw new Error("bad origin");
        }

        wss.handleUpgrade(req, socket, head, (ws) => {
            wss.emit("connection", ws, req, payload);
        });
    } catch (err) {
        socket.write("HTTP/1.1 401 Unauthorized\r\n\r\n");
        socket.destroy();
    }
});

// Helper: spawn an ephemeral container with a TTY
async function createSandboxContainer({ uid = 1000, gid = 1000 } = {}) {
    // Ensure the image is present (pull out-of-band in production to avoid cold starts)
    const container = await docker.createContainer({
        Image: IMAGE,
        Cmd: ["/bin/sh"],
        Tty: true,
        OpenStdin: true,
        StdinOnce: false,
        Env: ["TERM=xterm-256color"],
        WorkingDir: "/workspace",
        User: `${uid}:${gid}`,
        HostConfig: {
            AutoRemove: true,
            Memory: 256 * 1024 * 1024, // 256 MiB
            NanoCpus: 500_000_000, // 0.5 CPU
            PidsLimit: 256,
            CapDrop: ["ALL"],
            SecurityOpt: ["no-new-privileges"],
            ReadonlyRootfs: false, // flip to true for locked-down images
            Tmpfs: { "/tmp": "rw,size=64m,mode=1777" },
            // DNS, network mode, and egress restrictions would go here
        },
    });

    await container.start();
    return container;
}

function now() {
    return Date.now();
}

wss.on("connection", async (ws, req, auth) => {
    let idleDeadline = now() + IDLE_MS;
    let pingInterval = null;
    let container = null;
    let attachStream = null;
    let paused = false;

    const closeWith = (code, reason) => {
        try {
            ws.close(code, reason);
        } catch {}
    };

    try {
        container = await createSandboxContainer({ uid: 1000, gid: 1000 });

        // Attach after start; with TTY=true, stdout/stderr are multiplexed into one stream
        attachStream = await container.attach({
            stream: true,
            stdin: true,
            stdout: true,
            stderr: true,
        });

        // Periodic ping to detect dead peers
        pingInterval = setInterval(() => {
            try {
                ws.ping();
            } catch {}
        }, 30_000);

        ws.on("pong", () => {
            idleDeadline = now() + IDLE_MS;
        });

        // Flow: container -> ws
        attachStream.on("data", (chunk) => {
            if (ws.readyState !== WebSocket.OPEN) return;
            if (ws.bufferedAmount > MAX_WS_BUFFER) {
                if (!paused) {
                    attachStream.pause();
                    paused = true;
                }
                return; // drop until buffer drains; we resume in the send callback or timer below
            }

            ws.send(chunk, { binary: true }, () => {
                // Resume when kernel tx buffer freed
                if (paused && ws.bufferedAmount < MAX_WS_BUFFER / 2) {
                    attachStream.resume();
                    paused = false;
                }
            });
        });

        attachStream.on("error", () => closeWith(1011, "docker stream error"));

        // Flow: ws -> container
        ws.on("message", async (msg, isBinary) => {
            idleDeadline = now() + IDLE_MS;

            // Protocol: binary = keystrokes; text = control JSON (e.g., resize)
            if (isBinary) {
                try {
                    attachStream.write(msg);
                } catch {}
                return;
            }

            try {
                const control = JSON.parse(msg.toString("utf8"));
                const schema = z.object({
                    type: z.enum(["resize"]),
                    cols: z.number().int().min(1).max(500),
                    rows: z.number().int().min(1).max(200),
                });
                const { type, cols, rows } = schema.parse(control);
                if (type === "resize") {
                    // Resize the TTY attached to the *container's* primary process
                    await container.resize({ h: rows, w: cols });
                }
            } catch {
                // ignore malformed control messages
            }
        });

        ws.on("close", async () => {
            try {
                attachStream.end();
            } catch {}
            try {
                await container.kill({ signal: "SIGKILL" });
            } catch {}
            if (pingInterval) clearInterval(pingInterval);
        });

        ws.on("error", () => {
            try {
                attachStream.destroy();
            } catch {}
            try {
                container.kill({ signal: "SIGKILL" });
            } catch {}
            if (pingInterval) clearInterval(pingInterval);
        });

        // Idle reaper
        const idleTimer = setInterval(async () => {
            if (now() > idleDeadline) {
                try {
                    await container.kill({ signal: "SIGKILL" });
                } catch {}
                clearInterval(idleTimer);
                closeWith(1000, "idle timeout");
            }
        }, 5000);

        // Finally, start reading/writing
        container.modem && container.modem.followProgress
            ? null // no-op; included to show where you'd hook build/pull progress
            : null;
    } catch (err) {
        try {
            if (container) await container.remove({ force: true });
        } catch {}
        closeWith(1011, "failed to start sandbox");
    }
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
    console.log(`server listening on :${PORT}`);
});

// Helper: issue a short-lived JWT for the client (e.g., from your app server)
// Example only — you’d do this in your regular HTTP auth flow.
app.get("/token", (req, res) => {
    const payload = { sub: "user-123", scope: "sandbox:attach" };
    const token = jwt.sign(payload, JWT_SECRET, { expiresIn: "5m" });
    res.json({ token });
});
```

A few notes:

-   We attach to the container’s primary process (`/bin/sh`) with `TTY=true` so interactive behavior matches a local terminal.
-   Control messages (resize) are JSON; keystrokes are binary. This keeps the hot path simple.
-   Backpressure uses `ws.bufferedAmount` to pause/resume the Docker stream.

---

## 6) The browser side: xterm.js, resize, keystrokes

The front end is small thanks to xterm.js. We’ll open a WebSocket, render bytes, send keystrokes, and notify the server on resize.

### `index.html`

```html
<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8" />
        <title>Sandbox Terminal</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <!-- xterm.js from unpkg CDN -->
        <link rel="stylesheet" href="https://unpkg.com/xterm/css/xterm.css" />
        <style>
            html,
            body {
                height: 100%;
                margin: 0;
                background: #0b0f14;
            }
            #terminal {
                height: 100%;
            }
        </style>
    </head>
    <body>
        <div id="terminal"></div>
        <script src="https://unpkg.com/xterm/lib/xterm.js"></script>
        <script src="https://unpkg.com/xterm-addon-fit/lib/xterm-addon-fit.js"></script>
        <script>
            (async function main() {
                // Fetch a short-lived JWT from your app (this example assumes same origin)
                const { token } = await fetch("/token").then((r) => r.json());

                const term = new window.Terminal({
                    fontFamily: "Menlo, Consolas, monospace",
                    fontSize: 14,
                    cursorBlink: true,
                    convertEol: true,
                    theme: { background: "#0b0f14" },
                });
                const fit = new window.FitAddon.FitAddon();
                term.loadAddon(fit);
                term.open(document.getElementById("terminal"));
                fit.fit();

                const protocol = location.protocol === "https:" ? "wss" : "ws";
                const ws = new WebSocket(
                    `${protocol}://${
                        location.host
                    }/term?token=${encodeURIComponent(token)}`
                );
                ws.binaryType = "arraybuffer";

                ws.onopen = () => {
                    // Send initial size on connect
                    const { cols, rows } = term;
                    ws.send(JSON.stringify({ type: "resize", cols, rows }));
                    term.focus();
                    term.write("\x1b[32mWelcome to your sandbox!\x1b[0m\r\n");
                };

                ws.onmessage = (ev) => {
                    if (typeof ev.data === "string") {
                        // (reserved for future control messages from server)
                        return;
                    }
                    const data = new Uint8Array(ev.data);
                    term.write(data);
                };

                ws.onclose = (ev) => {
                    term.write(
                        `\r\n\x1b[31m[disconnected: ${
                            ev.reason || ev.code
                        }]\x1b[0m\r\n`
                    );
                };

                ws.onerror = () => {
                    term.write("\r\n\x1b[31m[connection error]\x1b[0m\r\n");
                };

                // Send keystrokes as binary
                term.onData((s) => {
                    const bytes = new TextEncoder().encode(s);
                    if (ws.readyState === WebSocket.OPEN) ws.send(bytes);
                });

                // Resize handling
                const sendResize = () => {
                    fit.fit();
                    if (ws.readyState === WebSocket.OPEN) {
                        ws.send(
                            JSON.stringify({
                                type: "resize",
                                cols: term.cols,
                                rows: term.rows,
                            })
                        );
                    }
                };
                window.addEventListener("resize", sendResize);
            })();
        </script>
    </body>
</html>
```

This is everything you need to get a responsive shell in the browser. Try `ls`, `node --version`, or even `npm init -y` in the container.

---

## 7) Authentication & authorization: short-lived tokens and origin checks

Security posture for terminals:

-   **Short-lived JWTs (2–5 minutes)**: your regular app flow issues a token that only authorizes “attach to sandbox.”
-   **Origin checks**: on upgrade, ensure `Origin` matches allowed domains.
-   **Per-session scope**: include a container/session ID in the JWT if you pre-create sandboxes.
-   **No cookies** for WS auth: send tokens explicitly in the URL or headers to avoid CSRF surfaces, and verify them server-side.
-   **Rate limiting**: protect `/token` and WebSocket upgrade endpoints (e.g., IP-based token bucket).
-   **Audit trail**: record `sub`, IP, timestamps for connect/disconnect.

If you prefer session cookies, consider binding a CSRF token to the WS upgrade via a custom header and verify it before `handleUpgrade`.

---

## 8) Lifecycle & cleanup: cold starts, idle reap, and zombie hunts

A production sandbox service handles the messy edges:

-   **Cold start**: pulling images is slow. Pre-pull images on each host and periodically refresh them. For heavy images, build variants with only what you need for the terminal use case.
-   **Idle reap**: stop containers after a period of inactivity to free resources. We used a rolling `idleDeadline`.
-   **Disconnects**: if the browser drops, kill the container unless you support “reconnect to the same session” semantics.
-   **Zombie cleanup**: crash loops happen. Daemons restart. Run a periodic janitor that removes orphaned containers matching your label (e.g., `label=sandbox=true` and `status=exited`).
-   **Concurrency policy**: do you allow multiple browsers to attach to the same session? Default to “one writer,” optionally add “read-only mirrors.”

Consider adding Docker labels like:

```js
Labels: {
  'sandbox': 'true',
  'user': auth.sub,
  'created_by': 'webterm',
}
```

This simplifies janitor scripts and metrics.

---

## 9) Performance tuning: cutting tail latency

Interactive “feel” lives in p95/p99, not averages. A few practical dials:

-   **Co-locate** the WS server and Docker daemon (Unix socket). Don’t hop over the network if you can avoid it.
-   **Disable message compression** (already done) and **avoid base64**.
-   **Set `TCP_NODELAY`** on Node’s underlying socket (the `ws` library enables this by default).
-   **Right-size TTY**: fewer columns/rows means fewer bytes on a full repaint.
-   **Backpressure**: we paused the Docker stream when `ws.bufferedAmount` spikes. Tune thresholds.
-   **Proxy config**: if you terminate TLS at NGINX/Envoy, disable proxy buffering for the WS path and crank timeouts:

    -   `proxy_request_buffering off; proxy_buffering off; proxy_read_timeout 1h;`

-   **Pre-warm**: keep a small pool of ready containers if your workload has predictable bursts.
-   **Lean images**: `alpine`-based images with only essentials cut container start time and reduce CVE surface.

If you still see jitter, record timestamps at each hop (browser send → server receive → docker write → docker read → server send → browser receive). This helps pinpoint whether the bottleneck is network, kernel buffers, or container CPU starvation.

---

## 10) Hardening beyond Docker: gVisor/Kata/Firecracker

Containers share the host kernel. If your threat model includes malicious code (it does), consider additional isolation:

-   **gVisor (runsc)**: user-space kernel that intercepts syscalls. Drop-in runtime (`--runtime=runsc`) with better isolation at modest overhead.
-   **Kata Containers**: lightweight VMs under your containers—stronger isolation with a small VM overhead.
-   **Firecracker/MicroVMs**: fast-boot VMs used by serverless platforms. Combine with a jailer for strong boundaries; you’ll trade higher complexity and slightly slower cold starts.

You can expose a toggle at scheduling time: high-risk sessions (e.g., anonymous users) run under gVisor/Kata; trusted org accounts use runc for speed.

---

## 11) Observability & auditing

Treat the terminal as a production service:

-   **Structured logs**: WebSocket connect/disconnect, JWT subject, container ID, exit code, duration, byte counts in/out, throttling events.
-   **Metrics**: container start latency, attach latency, bytes/s per session, error rates, p95 p99 round-trip for a small echo (you can periodically send `\r\n` and measure time to render a sentinel in the browser).
-   **Tracing**: instrument the upgrade path and Docker API calls with OpenTelemetry; sampling at low rates is enough.
-   **Session recording** (optional): if your policy allows, capture terminal streams for abuse investigations. If you do, encrypt at rest and set a clear retention period.

---

## 12) Putting it all together: a quick end-to-end test

1. Build the server and HTML files.
2. Ensure Docker is running and the `node:20-alpine` image is pulled.
3. Start the Node server: `node server.js`
4. Open `http://localhost:3000/index.html` (serve it from Express or a static server).
5. You should see a shell. Try `cat /etc/os-release`, `node -v`, `apk add curl` (if not read-only).
6. Resize the window; `$COLUMNS` should update.

If the terminal is sluggish, check:

-   Browser devtools → WS frames: ensure you see **binary** frames, not base64.
-   Server logs: are you constantly pausing the Docker stream? Lower `MAX_WS_BUFFER` or inspect client CPU.
-   Proxy: confirm it isn’t buffering or closing idle connections.

---

## 13) Variations and production concerns

-   **Command execution instead of shells**: For build/test sandboxes, use `docker.exec` per command rather than a long-lived shell. You’ll need a small command protocol over WS.
-   **Persistent workspaces**: Mount a per-user volume (scoped by org/project), but be strict with quotas and scan for malware.
-   **Read-only mirrors**: Add a mode where multiple viewers can watch one session (e.g., mentorship, classrooms). Send the stream to all, but only one client writes.
-   **Rate limiting & quotas**: N requests/sec per IP for `/token`, M concurrent containers per user/org.
-   **Multi-region**: Place sandbox hosts near users; terminate TLS at the edge but keep the WS hop short to compute.
-   **Secrets**: Never inject long-lived credentials. If the sandbox needs access to private registries or APIs, use scoped, short-lived tokens and network policies.

---

## Key Takeaways

-   A great browser terminal is mostly plumbing: **binary, TTY, backpressure, and careful container flags**.
-   **Security first**: drop capabilities, run as non-root, restrict resources, and prefer read-only roots plus tmpfs.
-   **Latency lives in details**: skip compression, avoid extra hops, and tune buffering.
-   **Plan for mess**: idle reap, janitors, and observability turn a demo into a service.
-   For stronger isolation, consider **gVisor/Kata/Firecracker**—especially for untrusted users.

---

## Further Reading & Exploration

-   Docker security hardening guides (capabilities, seccomp, AppArmor)
-   xterm.js docs and addons (fit, web links, unicode support)
-   `ws` library docs (backpressure, perMessageDeflate, ping/pong)
-   gVisor and Kata Containers documentation
-   OpenTelemetry for Node.js (instrumenting HTTP/upgrade flows)

---

### Appendix: `docker exec` variant (if you prefer exec over attach)

If you start a container with a minimal init (e.g., `sleep infinity`) and then exec a shell per WS session:

```js
const exec = await container.exec({
    Cmd: ["/bin/sh"],
    AttachStdin: true,
    AttachStdout: true,
    AttachStderr: true,
    Tty: true,
});
const stream = await exec.start({ hijack: true, Tty: true });
// stream is duplex; wire it to ws as above
await exec.resize({ h: rows, w: cols }); // for window size changes
```

This keeps the base container alive while sessions come and go. The trade-off is complexity (you must reap execs) vs. slightly faster “shell ready” times.

---

If you’ve made it this far, you’ve got all the pieces to stand up a real-time, reasonably hardened sandbox. Start simple, instrument everything, and iterate. Your future self debugging a p99 spike at 2 a.m. will thank you.
