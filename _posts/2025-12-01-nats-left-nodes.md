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
    overlay_image: /assets/images/nats-left-nodes/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/nats-left-nodes/banner.png
title: "Bridging the Edge: Using NATS Leaf Nodes to Build Hybrid and Multi-Cloud Systems"
tags:
    - nats
    - distributed messaging
---

If you’re running anything remotely serious today, your architecture probably isn’t “just” in one place.

You’ve got:

-   A primary cluster in one cloud,
-   Some workloads in another provider “for redundancy,”
-   A few on‑prem data centers that stubbornly refuse to die,
-   And maybe thousands of edge sites: factories, stores, vehicles, sensors, or tiny Kubernetes clusters in odd places.

All of these want to talk to each other with **low latency**, **good reliability**, and **reasonable security**… without you building a bespoke spiderweb of tunnels, MQTT bridges, and hand‑rolled sync daemons.

This is exactly the kind of mess NATS leaf nodes are built for.

In this post we’ll walk through **what NATS leaf nodes are**, **how they work under the hood**, and **concrete patterns** for using them to stitch together hybrid, multi-cloud, and edge deployments into one coherent messaging fabric.

---

## 1. The hybrid & edge sprawl problem

Let’s start with the pain.

Imagine a global retail company:

-   A central analytics and services platform in `cloud-1`
-   Payment and fraud systems in `cloud-2`
-   Regional data centers for compliance reasons
-   1,700+ physical stores, each with local PoS, inventory, and IoT devices

You want:

-   **Local latency** in each store (tens of microseconds to a local broker, not 200 ms to the cloud)
-   **Global awareness** (central systems see telemetry, send commands, run analytics)
-   **Resilience to disconnects** (stores should keep running even if the WAN link dies)
-   **Strong isolation** between sites and tenants
-   **Minimal “just open this port” firewall negotiations**

You _can_ get there with a traditional cluster of brokers stretched across regions, plus VPNs, plus some sort of replication. But:

-   Large, geographically stretched clusters get **chatty** and fragile.
-   Firewalls and NATs make **incoming** connections annoying.
-   Edge sites often want a **local-first** behavior: keep traffic on-site unless it really needs to cross the WAN.
-   Multi-cloud and third‑party messaging services add **different ownership and security domains**.

NATS gives you a neat set of building blocks for this: **clusters**, **gateways** (for super‑clusters), and **leaf nodes**. Leaf nodes are the bit that makes hybrid/edge deployments feel natural, instead of duct‑taped.

---

## 2. NATS in 90 seconds (just enough to talk topology)

Quick refresher so the rest makes sense:

-   NATS is a **subject-based** messaging system with pub/sub and request/reply.
-   A single `nats-server` is tiny and fast.
-   You scale out with:

    -   **Clusters**: multiple servers in one logical NATS service, usually within a region or DC, for capacity and HA. ([NATS Docs][1])
    -   **Super-clusters**: multiple clusters linked with **gateways**, typically across regions/clouds, optimized for long-haul connections and “interest‑pruned” routing. ([NATS Docs][1])
    -   **Leaf nodes**: servers that connect _into_ a cluster or super‑cluster and act more like a specialized “NATS client that also serves local clients”.

NATS also has **accounts** for multi-tenancy: each account has its own subject namespace and set of users. Accounts can **import/export** specific streams or services, letting you share data across boundaries without smashing all subjects into one global space. ([NATS Docs][2])

We’ll lean on all of this in the rest of the post.

---

## 3. What is a leaf node, really?

Conceptually, a **leaf node** is a NATS server you run “at the edge” that:

-   Accepts client connections locally,
-   Dials out to a **remote NATS system** (a cluster, super‑cluster, or managed service),
-   **Forwards only the traffic that’s allowed and necessary**, and
-   Keeps working locally even if the connection to the upstream hub goes away.

From the NATS docs, a leaf node:

-   **Extends an existing NATS system** of any size,
-   Can **bridge separate operators/security domains**, and
-   **Authenticates local clients itself**, with a separate auth policy from the hub. ([NATS Docs][3])

Traffic between the leaf node and the hub:

-   Uses a specific **user/account** on the hub side.
-   Only **subjects that user is allowed to publish** are exported from the leaf.
-   Only **subjects that user is allowed to subscribe to** are imported into the leaf. ([NATS Docs][3])

This gives you a very powerful mental model:

> The hub sees each leaf node as “one connection owned by this account.”
>
> The leaf node, in turn, manages many local clients and decides what flows up or down.

Leaf nodes also have some key properties that make them great for hybrid architectures:

-   They are **dial‑out only**: the leaf connects to the hub; the hub doesn’t need an inbound route to the edge site (great for NAT and strict firewalls). ([NATS Docs][3])
-   They can connect to the hub via **TLS** or **WebSockets** (useful for crossing corporate proxies). ([NATS Docs][1])
-   They participate in an **acyclic topology**: you can build trees of leaf nodes, but you avoid cycles and the routing nightmares they cause. ([NATS Docs][3])

Visually, think:

```text
       +------------------+         +------------------+
       |  Hub NATS        |         |  Hub NATS        |
       |  cluster / SC    |  ...    |  cluster / SC    |
       +---------+--------+         +---------+--------+
                 ^                            ^
                 | leaf connection            | leaf connection
                 v                            v
           +-----+-------+              +-----+-------+
           | Leaf node   |              | Leaf node   |
           | (store #1)  |              | (factory)   |
           +--+-------+--+              +--+-------+--+
              ^       ^                    ^       ^
        local apps  devices          local apps  devices
```

Each leaf node gives its site a **local NATS** that happens to be plugged into a much larger fabric.

---

## 4. Why leaf nodes are perfect for hybrid & edge

Let’s map leaf node behavior to requirements we had earlier.

### 4.1 Local-first, low-latency behavior

Leaf nodes forward traffic **only when needed** and preserve NATS’ queue semantics:

-   If a service or queue consumer exists **locally** on the leaf, requests from local clients go there first.
-   Only when there’s no suitable local consumer will the leaf send the request upstream. ([NATS Docs][1])

This is exactly what you want for edge sites:

-   Local control loops stay on-site (fast).
-   Global services are still reachable (fall back to the hub).

### 4.2 Clean security & tenancy boundaries

Because the hub only sees a **single user/account** for each leaf connection, you have a clean point to enforce:

-   Which subjects this site is allowed to **publish up** (telemetry, logs, events).
-   Which subjects it can **receive from the hub** (commands, configs, global requests).

This makes it straightforward to:

-   Enforce **data residency** (e.g., certain data never leaves the EU region),
-   Isolate tenants (accounts per customer, leaf nodes per site),
-   Keep local auth logic under local control.

Synadia’s “Adaptive Edge Architecture” leans heavily on this: clusters in data centers or clouds act as hubs, **leaf nodes extend connectivity into edge sites**, and accounts + exports/imports enforce who can see what. ([NATS.io][4])

### 4.3 Works with partially connected edge

Leaf nodes keep providing service to local clients even when the uplink to the hub is down. With JetStream enabled, you can:

-   Persist local events in an **edge JetStream stream**,
-   Mirror or source them into **hub JetStream streams** once connectivity returns. ([NATS Docs][5])

This is the “store‑and‑forward” pattern needed for IoT, retail stores, vehicles, ships, etc., where WAN connectivity is intermittent. Real-world deployments use thousands of leaf nodes at the edge, each syncing data into a central cluster this way. ([GitHub][6])

### 4.4 Multi-cloud and managed NATS

Because leaf nodes can connect to **any NATS cluster** (self-managed or SaaS), they’re a great way to:

-   Attach local servers or clusters as leaf nodes to a managed NATS network (e.g., Synadia Cloud). ([NATS Docs][3])
-   Bridge **separate operators** and security domains without merging their configuration. ([NATS Docs][3])

You get a **single, global connectivity plane** without asking every edge site to know every other site.

---

## 5. Under the hood: how leaf nodes route traffic

Let’s zoom in a bit on how a leaf node behaves internally.

### 5.1 Two perspectives: local vs hub

A leaf node sits between two worlds:

-   **Local side**

    -   Accepts client connections as a normal NATS server.
    -   Authenticates and authorizes them using **local config**.
    -   Maintains a local subscription “interest graph”.

-   **Hub side**

    -   Connects to the hub as **one NATS client connection**, using credentials from some account. ([NATS Docs][3])
    -   Subscribes/publishes based on local interest _filtered_ by what that user/account is allowed to do.
    -   Receives imported messages and redistributes them to local subscribers.

Conceptually:

```text
[ local client A ] -> [ leaf node ] ==(one conn)==> [ hub cluster ]
[ local client B ] <-            ^                 [ account HUB  ]
                               auth
```

### 5.2 Interest propagation

When a local client subscribes to `sensor.temp.store1`:

1. The leaf node records this local subscription.
2. It checks whether the **hub-side user** is allowed to subscribe to that subject.
3. If allowed, it creates a corresponding subscription over the leaf connection.
4. The hub’s interest graph now knows: “someone in account HUB is interested in `sensor.temp.store1` through this connection.”

When a message is published on the hub to `config.*`:

-   The hub sends it only over leaf connections whose remote side expressed interest.
-   The leaf forwards it to matching local subscribers (again subject to local permissions).

Because all of this is subject-based and interest-pruned, you avoid blasting all messages to all leaf nodes.

### 5.3 Queue groups and “nearest service wins”

For **queue groups** and services, NATS ensures that local consumers are preferred:

-   If there’s a queue group `orders.process` with members both on the hub and on the leaf,
-   And a client connected to the leaf sends a request,
-   The leaf will route that request to a **local** member if any exist, and only go upstream if none are available. ([NATS Docs][1])

That gives you a natural hierarchy:

-   Run services locally when possible,
-   Let central services backstop them.

### 5.4 Topology and reachability

Leaf nodes are asymmetrical:

-   They **dial out** to the hub (like a client),
-   They **do not need inbound connectivity** from the hub. ([NATS Docs][3])

This is hugely useful in environments where:

-   Edge sites sit behind NAT or firewalls,
-   Only outbound TLS or WebSocket traffic is allowed. ([NATS Docs][1])

NATS encourages **acyclic graphs** of leaf connections: you can build trees like:

```text
global hub cluster
    ^
    |
 regional leaf (cloud region)
    ^
    |
 site leaf (store / factory)
```

But you avoid loops that would create ambiguous routing paths.

---

## 6. A worked example: “branch office” leaf node

Let’s build a small but realistic example: a branch/site with a local NATS leaf node that connects back to a central hub.

### 6.1 Hub configuration (cloud/data center)

We’ll assume you already have a NATS cluster acting as the hub. On one of the servers, you configure it to accept leaf connections:

```conf
# hub.conf
port: 4222

leafnodes {
  # Where leaf nodes will connect to this hub
  port: 7422
}

# Simple local auth: one account, two users
accounts: {
  HUB: {
    users: [
      { user: "api",  password: "api-secret"  },  # normal app clients
      { user: "leaf", password: "leaf-secret" }   # leaf nodes connect as this user
    ]
  }
}
```

Start the hub server:

```bash
nats-server -c hub.conf
```

You’d normally run multiple hub servers in a **cluster** or **super‑cluster**, with this `leafnodes { port: ... }` block on each. ([NATS Docs][1])

### 6.2 Leaf node configuration (edge site)

On the branch’s local server (maybe a tiny VM or K8s node), you run another `nats-server`, but as a leaf node:

```conf
# branch.conf
port: 4222          # local clients connect here

leafnodes {
  remotes: [
    {
      # Dial out to the hub’s leafnode port over TLS
      url: "tls://leaf:[email protected]:7422"
    }
  ]
}
```

Start it:

```bash
nats-server -c branch.conf
```

At this point:

-   Local applications in the branch connect to `nats://localhost:4222`.
-   The leaf node dials `hub:7422` using the `leaf` user, enforcing whatever permissions you configure for that user.

### 6.3 Testing the behavior

Set up a service on the hub:

```bash
# Run this near the hub, using the api user:
nats reply --server "nats://api:[email protected]:4222" "greet" "hello from hub"
```

Now from the branch, send a request via the leaf node:

```bash
# From the branch site:
nats req --server "nats://localhost:4222" "greet" ""
```

You’ll get `hello from hub` back, routed through the leaf connection.

Now add a local service at the branch on the same subject:

```bash
# On the branch:
nats reply --server "nats://localhost:4222" "greet" "hello from branch"
```

Send a few more requests from the branch. You’ll see NATS prefers the **local** service on the leaf node, only falling back to the hub if the local one goes away. ([NATS by Example][7])

This tiny example illustrates the core behavior you want for hybrid systems:

-   Local services serve local clients fast.
-   Central services are still reachable without any code changes.

---

## 7. Leaf nodes vs gateways vs “just one huge cluster”

When should you use which NATS topology building block?

### 7.1 Cluster

Use a **cluster** when:

-   Servers are in the **same region or LAN**, with low latency between them.
-   You want **HA and capacity** within that locality.

### 7.2 Super‑cluster (gateways)

Use **gateways** to connect clusters into a **super‑cluster** when:

-   You have **multiple regions or clouds** that are _peers_ (e.g., us‑east, us‑west, eu‑central).
-   Clients in each region should see each other as part of one logical NATS deployment.
-   You want optimized, interest‑pruned routing across regions without stretching a single cluster too widely. ([NATS Docs][1])

### 7.3 Leaf nodes

Use **leaf nodes** when:

-   You’re crossing **network ownership / security boundaries** (edge → cloud, customer site → your SaaS, on‑prem → managed NATS).
-   The remote side cannot or should not host a full cluster member (e.g., no inbound connectivity).
-   You want **local‑first** semantics and the ability to **restrict** what flows in/out via hub‑side account permissions.

A common pattern in multi-cloud:

```text
[ Cloud A cluster ] <-- gateway --> [ Cloud B cluster ]
       ^                                    ^
       | leaf nodes                         | leaf nodes
     edge sites A                         edge sites B
```

Where:

-   Gateways handle **peer clouds** (cloud ↔ cloud).
-   Leaf nodes handle **sites and edges** (site ↔ hub).

Frameworks like wasmCloud explicitly recommend hub‑and‑spoke and hub‑spoke‑spoke patterns built on NATS leaf nodes for this reason. ([wasmCloud][8])

---

## 8. JetStream + leaf nodes: offline edge, online analytics

So far we’ve mostly talked about **ephemeral** messaging. What about persistent streams and replay?

JetStream is NATS’ persistence layer, and it plays very nicely with leaf nodes.

### 8.1 JetStream domains and “islands”

A key idea from the NATS docs: you can run **independent JetStream instances** (islands) connected via leaf nodes, but you need a way to tell them apart. That’s what **JetStream `domain`** is for. ([NATS Docs][5])

Example from the docs, simplified:

```conf
# hub.conf
port: 4222
server_name: hub-server

jetstream {
  store_dir: "./store_server"
  domain: "hub"
}

leafnodes {
  port: 7422
}

include "./accounts.conf"
```

```conf
# leaf.conf (edge site)
port: 4222
server_name: branch-1

jetstream {
  store_dir: "./store_leaf"
  domain: "branch-1"
}

leafnodes {
  remotes: [
    {
      urls: ["nats://admin:[email protected]:7422"]
      account: "ACC"
    }
  ]
}

include "./accounts.conf"
```

Because the domains are different (`hub` vs `branch-1`), JetStream APIs are available under:

-   `$JS.hub.API.>` for the hub domain
-   `$JS.branch-1.API.>` for the branch domain ([NATS Docs][5])

A client can be connected anywhere (hub or leaf) and still target specific domains when managing or consuming streams.

### 8.2 Mirroring and sourcing across domains

Now the fun part: crossing domains.

You can:

-   **Mirror** a stream from one domain into another (think backup / read replica).
-   **Source** multiple streams from leaf domains into an aggregated stream in the hub. ([NATS Docs][5])

For example, suppose each branch has a `transactions` stream in its own JetStream domain. You can create a hub stream that **sources** from those leaf streams:

```bash
# On the hub, create an aggregate stream from branch-1:
nats stream add --js-domain hub --source transactions
# During prompts, specify that the source comes from domain "branch-1"
```

The docs show how to specify a foreign JetStream domain when adding `source` or `mirror`. Once configured, messages are **copied** from leaf streams into hub streams and are accessible even if the leaf connection later goes offline. ([NATS Docs][5])

This is exactly the pattern you want for:

-   **IoT telemetry aggregation** from many sites,
-   Local buffering during outages,
-   Global analytics and compliance storage at the hub.

---

## 9. Security, TLS, and “sidecar” patterns

Security-wise, leaf nodes give you a nice separation of concerns.

### 9.1 Local clients vs leaf connection

On a leaf node:

-   **Local clients** authenticate however you like: username/password, nkeys, JWT accounts, or even anonymous if you trust the host. ([NATS Docs][3])
-   The **leaf connection** itself authenticates to the hub with its own user credentials, configured in the hub’s account.

This enables a very handy pattern seen in wasmCloud and others:

-   Run a **leaf node sidecar** next to an app platform.
-   Apps connect to `nats://localhost` with no credentials.
-   The leaf node holds the actual credentials and does the secure leaf connection to the hub. ([wasmCloud][8])

You centralize sensitive credentials at the leaf node and dramatically simplify deployment for local workloads.

### 9.2 TLS and TLS-first handshake

For network security:

-   Leaf node connections can use **TLS** or **WebSockets**. ([NATS Docs][3])
-   As of NATS v2.10, you can configure **TLS-first** behavior for leaf nodes: instead of sending a clear‑text INFO message before negotiating TLS, the servers can be configured to perform a TLS handshake first, then exchange INFO. This matters in environments where _any_ clear‑text on that port is forbidden. ([NATS Docs][3])

On top of that, account-level exports/imports let you surgically control exactly which subjects cross the leaf connection, so security policy is not “all or nothing.”

---

## 10. Design tips and common pitfalls

Before we wrap up, a few practical tips if you’re planning to go big with leaf nodes.

### 10.1 Be explicit about “local” vs “global” subjects

Use clear subject patterns and account permissions to model where data should live:

-   Local-only data: `site.<site-id>.local.>`, only allowed to publish/subscribe locally.
-   Uplink telemetry: `site.<site-id>.telemetry.>`, allowed to publish up to the hub.
-   Downlink commands: `site.<site-id>.control.>`, allowed to subscribe from the hub.

Then:

-   On the **hub**, restrict the leaf user to only publish/subscribe to the appropriate prefixes.
-   On the **leaf**, keep local-only subjects accessible but not imported/exported.

This gives you easy answers to “does this ever leave the site?”

### 10.2 Plan your accounts

Use **more accounts with simple rules** rather than one monster account with complex authorization. Accounts act as “messaging containers” for applications or tenants and can be selectively connected via exports/imports. ([NATS Docs][2])

Common patterns:

-   Account per tenant, with one or more leaf nodes per tenant site.
-   Account per major application domain (telemetry, commands, admin).

### 10.3 Think about operational tooling

Leaf-node-heavy deployments are still just NATS:

-   You can use the **system account** and the `nats` CLI to introspect leaf connections, accounts, JetStream state, etc. ([NATS Docs][9])
-   Consider exporting system events into an observability pipeline to track when leaf nodes connect/disconnect, how much traffic flows per site, etc.

### 10.4 Avoid topological surprises

-   Keep leaf graphs **acyclic**; think trees and forests, not arbitrary meshes.
-   If you have lots of leaves (hundreds or thousands of stores/factories), design your hub cluster capacity and JetStream storage strategy with aggregate throughput in mind. It’s proven to work at that scale, but it still requires capacity planning. ([GitHub][6])

---

## 11. Key takeaways

Let’s recap the main ideas:

-   **Leaf nodes are NATS servers that act as local “edge brokers” while dialing out to a hub cluster or managed NATS network.** They extend connectivity across regions, clouds, and security domains without flattening everything into one giant cluster. ([NATS Docs][3])

-   They provide **local‑first, low-latency behavior**: local services and queue consumers are preferred; only remaining traffic crosses the leaf connection, which is interest‑pruned and subject‑scoped.

-   Leaf nodes are ideal for **hybrid and multi-cloud systems**:

    -   Connect VPCs and data centers.
    -   Attach edge sites (stores, factories, vehicles).
    -   Plug your environment into managed NATS services like Synadia Cloud. ([NATS Docs][3])

-   With **JetStream domains and mirror/source**, you can build **offline-capable edge streams** that sync into centralized analytics streams in the hub, using store‑and‑forward semantics. ([NATS Docs][5])

-   Security remains clean:

    -   Local clients auth to the leaf.
    -   Leaf auths to the hub as a single user/account.
    -   Permissions and account exports/imports define exactly what crosses boundaries.
    -   TLS and TLS-first handshake keep wire security tight. ([NATS Docs][3])

If you squint, leaf nodes turn your scattered infrastructure into one big **data grid** with built-in locality and security, instead of a collection of bespoke tunnels and sync scripts.

---

## 12. Further reading & next steps

If you want to go deeper, these are great next steps:

-   **NATS Leaf Nodes docs** – core concepts, config, and tutorials. ([NATS Docs][3])
-   **JetStream on Leaf Nodes** – how to use domains, mirrors, and sources across hubs and leaves. ([NATS Docs][5])
-   **NATS Adaptive Deployment Architectures** – how clusters, super‑clusters, and leaf nodes fit together. ([NATS Docs][1])
-   **NATS by Example – Simple Leafnode** – runnable example with the `nats` CLI showing local‑first routing. ([NATS by Example][7])
-   **wasmCloud: NATS Leaf Nodes & Sidecars** – a concrete platform that leans on leaf nodes for edge and sidecar patterns. ([wasmCloud][8])

From here, a fun exercise is to:

1. Stand up a small **hub cluster** locally with Docker or Kubernetes,
2. Run a couple of **leaf nodes** on your laptop or on remote VMs,
3. Play with subject permissions and JetStream domains,
4. Watch how traffic flows as you move services between hub and leaf.

You’ll get an intuitive feel for how NATS leaf nodes let you bridge the edge without losing your mind—or your latency budget.

[1]: https://docs.nats.io/nats-concepts/service_infrastructure/adaptive_edge_deployment "NATS Adaptive Deployment Architectures | NATS Docs"
[2]: https://docs.nats.io/running-a-nats-service/configuration/securing_nats/accounts?utm_source=thinhdanggroup.github.io "Multi Tenancy using Accounts | NATS Docs"
[3]: https://docs.nats.io/running-a-nats-service/configuration/leafnodes "Leaf Nodes | NATS Docs"
[4]: https://nats.io/blog/synadia-adaptive-edge/ "Introducing the Synadia Adaptive Edge Architecture | NATS blog"
[5]: https://docs.nats.io/running-a-nats-service/configuration/leafnodes/jetstream_leafnodes "JetStream on Leaf Nodes | NATS Docs"
[6]: https://github.com/nats-io/nats-server/discussions/5974?utm_source=thinhdanggroup.github.io "Use thousands of leaf nodes at the edge · nats-io nats-server ..."
[7]: https://natsbyexample.com/examples/topologies/simple-leafnode/cli/ "NATS by Example - Simple Leafnode (CLI)"
[8]: https://wasmcloud.com/docs/reference/nats/leaf-nodes/ "NATS Leaf Nodes | wasmCloud"
[9]: https://docs.nats.io/running-a-nats-service/configuration/sys_accounts?utm_source=thinhdanggroup.github.io "System Events | NATS Docs"
