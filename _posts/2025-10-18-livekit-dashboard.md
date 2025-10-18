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
    overlay_image: /assets/images/livekit-dashboard/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/livekit-dashboard/banner.png
title: "Introducing LiveKit Dashboard: Simplifying Self-Hosted Real-Time Management"
tags:
    - LiveKit
    - Dashboard
---

## Why Managing LiveKit at Scale Feels Like Flying Blind

Running LiveKit at scale is powerful — but it can also feel like you’re managing a live concert with the lights off. You’ve got rooms, participants, servers, and recordings all moving at once, and without a clear dashboard, visibility becomes guesswork.

Typical pain points include:

-   SSH-ing into servers just to check logs
-   Writing ad-hoc scripts to query APIs
-   Manually tracking who’s connected where
-   Managing egress jobs without clear feedback
-   No unified view of SIP or telephony integrations

If that sounds familiar, you’ll immediately see why **LiveKit Dashboard** exists — it turns that scattered workflow into a single, actionable control panel.

---

## What Exactly Is LiveKit Dashboard?

LiveKit Dashboard is a **stateless**, **self-hosted** management app built with **FastAPI** and **Jinja2**. It communicates directly with your LiveKit servers using the official Python SDK — fetching live data on demand, with zero persistence or external dependencies.

### Design Principles That Keep It Simple

-   **Stateless by Design** – No database or background workers. Every request reflects real-time data.
-   **Self-Hosted First** – Deploy anywhere, stay in control of your infrastructure.
-   **Security-Focused** – Includes HTTP Basic Auth, CSRF protection, and hardened security headers.
-   **Progressively Enhanced** – Runs without JavaScript, upgraded with HTMX for real-time interactions.

---

## Key Features That Make Operations Easier

### 🏠 Overview Dashboard

![Overview Dashboard](/assets/images/livekit-dashboard/dashboard.png)

Your “cockpit view.”
Monitor room counts, participant distribution, SFU health, and API latency — refreshed every few seconds.

**Example**:
A DevOps engineer can spot API latency spikes within seconds instead of waiting for alerting tools to trigger. It’s like watching your cluster’s heartbeat live.

---

### 🚪 Room Management

![Room Management](/assets/images/livekit-dashboard/room.png)

Create, view, and control rooms instantly — with visibility into active participants, tracks, and session states.

**Real-World Use Case**:
Imagine a live streaming platform where a user reports “no video.” You open the dashboard, drill into the room, and see that their video track is muted — no SSH, no script, no waiting.

---

### 👥 Participant Controls

View participant connection health, media tracks, and latency metrics — and manage permissions or remove users with a single click.

This transforms support from “reactive triage” to “proactive resolution.”

---

### 📹 Egress and Recording Management

![Egress and Recording Management](/assets/images/livekit-dashboard/egress.png)

Start composite recordings, monitor live jobs, and download finished files — all from the browser.

**Before:**
Running curl commands and checking job IDs manually.
**After:**
Click “Start Recording,” watch the status live, and access the file when done.

---

### 📞 Optional SIP Integration

![Outbound Calls](/assets/images/livekit-dashboard/outbound-calls.png)
![Inbound Calls](/assets/images/livekit-dashboard/inbound-calls.png)

Manage SIP trunks, routing, and telephony workflows directly from the interface when enabled.

---

### 🧪 Token Generator Sandbox

Quickly generate test tokens with configurable roles and TTLs. Perfect for debugging or validating new room settings before deploying to production.

---

## Under the Hood: A Simple Yet Scalable Architecture

```
User Browser ─▶ FastAPI + Jinja2 (SSR) ─▶ LiveKitClient SDK ─▶ Your LiveKit Server
```

**Why this matters:**

-   **Horizontally scalable:** Run multiple instances with no coordination
-   **Always current:** Every page fetches live data
-   **Resilient:** Restart anytime — no state to lose
-   **Lightweight:** Minimal CPU and memory usage

---

## Getting Started in Minutes

### 🐳 With Docker

```bash
git clone <repository-url>
cd livekit-dashboard
cp .env.example .env  # Add your credentials
make docker-run
```

### 💻 Manual Setup

```bash
make install
export LIVEKIT_URL="https://your-livekit-server.com"
export LIVEKIT_API_KEY="your-api-key"
export LIVEKIT_API_SECRET="your-api-secret"
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="secure-password"
make dev
```

Then visit `http://localhost:8000` and log in — your LiveKit world, finally visible.

---

## Before & After: Real Operational Wins

### Scenario 1: Debugging Connection Issues

-   **Before:** Using CLI to query the API.
-   **After:** Open Dashboard → see 15 rooms, 127 participants → spot one room with connection drops → inspect the participant → fix instantly.

### Scenario 2: Recording Oversight

-   **Before:** Manually track egress job IDs.
-   **After:** Dashboard shows all active recordings, with real-time job status and instant access to download URLs.

### Scenario 3: Capacity Planning

-   **Before:** Write API queries to calculate load.
-   **After:** Dashboard overview shows distribution by room size and participant platform — updated automatically every few seconds.

These aren’t just convenience improvements — they directly reduce downtime and support overhead.

---

## Built for Real-Time Reliability

### Real-Time Analytics Example

```python
async def get_enhanced_analytics(self):
    # Fetch live participant metrics
    ...
    return {
        "connection_success": calculate_success_rate(),
        "platforms": {
            "Web": 60,
            "iOS": 20,
            "Android": 15,
            "React Native": 5
        }
    }
```

### Security First

```python
def verify_credentials(username, password):
    return secrets.compare_digest(username, expected_user) and \
           secrets.compare_digest(password, expected_pass)
```

Your credentials never leave your environment — no third-party calls, no logs.

---

## Current Limitations & Roadmap

**Today:**

-   Single admin account
-   No historical trend tracking (stateless)
-   Basic participant control (kick/mute only)

**Coming Soon:**

-   WebSocket updates
-   Rich participant analytics
-   Recording previews
-   Mobile-friendly UI
-   Optional persistent analytics

---

## Quick FAQ

**Does it work with LiveKit Cloud?**
No — it’s built for self-hosted LiveKit servers where you control API access.

**Is it secure?**
Yes — all data flows within your own environment. No external services involved.

**Can I extend it?**
Absolutely. Add routes, analytics, or custom integrations easily — it’s open and modular.

**Resource usage?**
Lightweight — runs on a single core and 512 MB of RAM.

---

## Example Configuration

```bash
LIVEKIT_URL=https://your-livekit-server.com
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure-password
ENABLE_SIP=false
```

---

## Why This Matters: From Monitoring to Mastery

For teams running real-time systems, visibility is power.
The **LiveKit Dashboard** turns management from reactive firefighting into confident, data-driven operation.

You don’t just “check if things work” — you _see_ them working.

**Start now**:

-   [View on GitHub](https://github.com/thinhdanggroup/livekit-dashboard)
-   [Read the Docs](https://github.com/thinhdanggroup/livekit-dashboard/blob/main/README.md)
-   [Explore the Architecture Guide](https://github.com/thinhdanggroup/livekit-dashboard/blob/main/docs/ARCHITECTURE.md)

Built with ❤️ for developers who love clarity and control.
