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
    overlay_image: /assets/images/kafka-to-nats/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/kafka-to-nats/banner.png
title: "From Kafka to NATS: When Less Is More in Distributed Messaging"
tags:
    - kafka
    - nats
    - distributed messaging
---

You’ve got a Kafka cluster humming in production. There are topics, partitions, consumer groups, dashboards, and an ever-growing list of “we’ll tune that later” configs.

Then someone on the team asks:

> “Do we really need _all_ of this just to send events between microservices?”

That question is pushing a lot of teams to look at lighter-weight messaging systems like **NATS**—especially NATS + **JetStream**. Kafka and NATS aren’t direct drop-in replacements, but they _do_ overlap in that messy middle of “events, queues, and services yelling at each other.”

This post is a hands-on, pragmatic tour of what happens when you go **from Kafka to NATS**—focusing on:

-   Architecture & mental models
-   Latency and throughput
-   Fault tolerance and durability
-   Operational complexity
-   A small “port this service” example in Go

By the end, you should have a pretty crisp sense of when _less_ (NATS) really is _more_ for your system—and when Kafka’s heavyweight log still earns its keep.

---

## 1. Two Different Worldviews: Log vs. Fabric

Before configs, benchmarks, and code, it helps to internalize something:

-   **Kafka is a durable, distributed log**
-   **NATS is a lightweight messaging fabric**

They overlap, but they’re optimized for different mental models.

### Kafka’s worldview: append-only history

Kafka is built around **topics** that are split into **partitions**, stored as **append-only logs** on disk. Producers write to partitions; consumers read from them in order, keeping track of their **offsets**. Topics are replicated across **brokers** for durability and high availability.([Instaclustr][1])

Modern Kafka (4.0+) uses **KRaft**, its own Raft-based consensus system, instead of ZooKeeper to manage metadata, leader election, and cluster state.([Cloudurable][2])

This design shines when:

-   You need **long-term retention** of events (hours, days, months, years)
-   You want **replay** and **event-sourcing**
-   You’re building **high-throughput data pipelines** and analytics streams

### NATS’s worldview: live messaging fabric

NATS started as a tiny, always-on pub/sub server with:

-   **Subjects** instead of topics (string names with wildcards, e.g. `orders.created.us.east`)
-   Built-in patterns: pub/sub, request–reply, and load-balanced queue groups
-   A focus on being **“always available”**, simple to operate, and easy to scale horizontally([GitHub][3])

Core NATS gives you **at-most-once**, in-memory messaging. Add **JetStream**, and you get:

-   Streams (durable logs _per subject pattern_)
-   Consumers (views on streams: pull or push)
-   Message replay, retention policies, and replication for fault tolerance([docs.nats.io][4])

JetStream is built into the `nats-server` binary and uses a Raft-based design for replication and durability.([sobyte.net][5])

NATS shines when:

-   You care about **ultra-low latency** and **operational simplicity**
-   You’re doing a lot of **service-to-service** messaging, request–reply, fan-out
-   You want a **cloud-native fabric** that runs comfortably in tight resource budgets([docs.nats.io][6])

Hold those worldviews. Everything else is a consequence.

---

## 2. Architecture Deep Dive: Kafka vs. NATS (+ JetStream)

Let’s peel the onion a bit.

### Kafka architecture in practice

Key pieces of Kafka’s architecture:([Instaclustr][1])

-   **Brokers** – Kafka servers forming a cluster
-   **Topics** – logical channels for messages
-   **Partitions** – shards of a topic distributed across brokers
-   **Producers** – send messages to topics
-   **Consumers** – read from partitions, often in **consumer groups**
-   **KRaft controllers** – manage metadata, leader election, ACLs, etc.

Each partition is an ordered, immutable log of records. Kafka does:

-   **Sequential disk writes** for peak throughput
-   **Replication** for durability and availability
-   **Batching & compression** to push millions of messages/sec

The tradeoff: **latency** is usually measured in **tens of milliseconds**, especially when you enable replication and durable semantics.([Onidel Cloud][7])

### NATS core: subjects and queues

Core NATS is deliberately simple:([GitHub][3])

-   **Subjects** – hierarchical strings (e.g. `users.created.us-east`) with `*` and `>` wildcards
-   **Publishers/Subscribers** – pub/sub over subjects
-   **Queue groups** – load-balanced consumers in a group
-   **Request–reply** – built-in RPC-style messaging

NATS servers form a **cluster**; clients can connect to any node, and messages are automatically routed across the cluster.([widhianbramantya.com][8])

Core NATS gives you:

-   **At-most-once** delivery
-   **In-memory**, non-durable messaging
-   **Blazing fast** sub-millisecond hops inside a cluster([My blog][9])

### NATS JetStream: persistence layered on top

JetStream adds the persistence and streaming bits Kafka gives you, but differently:([docs.nats.io][4])

-   **Streams** – durable, replicated storage for messages matching a subject (or set of subjects)
-   **Consumers** – stateful views on a stream; track delivery, acks, filters, replay
-   **Retention policies** – limits-based, work-queue, interest-based
-   **Delivery semantics** – at-most-once, at-least-once, and (under constraints) exactly-once in JetStream([docs.nats.io][6])

Internally, JetStream uses Raft-style replication and allows you to configure replication factors per stream (e.g., `R3`).([sobyte.net][5])

The twist vs. Kafka:

-   Kafka: global **cluster-wide** log per topic
-   JetStream: many **independent streams** scoped by subjects; you choose which subjects are persisted

You often end up with **core NATS** for “fast & ephemeral” and **JetStream** for “durable & replayable”—in the same cluster.

---

## 3. Latency & Throughput: Why NATS _Feels_ Faster

If you’ve ever sat in front of a dashboard and watched P99s creep up, this is the fun part.

### High-level numbers

Recent independent and vendor-related benchmarks paint a consistent picture:([My blog][9])

-   **NATS (core)**

    -   P99 latency: ~0.5–2 ms in-memory
    -   Throughput: up to millions of messages/sec on modest hardware

-   **NATS JetStream**

    -   P99 latency: sub-ms in-memory, typically 1–5 ms with persistence and replication
    -   Throughput: hundreds of thousands of persistent messages/sec

-   **Kafka**

    -   P99 latency: usually 10–50 ms under realistic persistence + replication
    -   Throughput: easily 500k–1M+ msg/sec with batching on standard VPS-class hardware

In other words:

> Kafka: **higher throughput**, higher latency.
> NATS: **lower latency**, still very high throughput, especially for core pub/sub.

The reasons:

-   Kafka **batches** aggressively and writes to disk—amazing for throughput, but you pay extra milliseconds.([Instaclustr][1])
-   NATS keeps a lot in memory and is tuned for quick hops across a mesh of servers. JetStream does write to disk, but the design still emphasizes low latency.([docs.nats.io][4])

### What this means for your system

You probably don’t care if an analytics pipeline is 15 ms vs. 2 ms slower.

But you _do_ care when:

-   You’re doing **request–reply** in front of a user
-   Microservices call each other dozens of times per request
-   IoT devices need **fast control-plane** round-trips

That’s where NATS tends to make a system _feel_ more responsive, especially in tail latencies—your P99s and P999s.

Kafka can absolutely handle low-latency workloads with careful tuning, but it’s not its “happy path.” NATS is optimized around that by default.

---

## 4. Fault Tolerance & Durability: Logs vs. Streams

Let’s look at what happens when things go wrong.

### Kafka’s durability and failover

Kafka’s durability story is excellent:([Instaclustr][1])

-   **Replication factor (RF)** per topic, commonly `3`
-   **In-sync replicas (ISR)** set; leaders only commit records when replicas ack
-   **KRaft controllers** manage partition leaders and metadata
-   Automatic leader election on broker failures

With proper settings (`acks=all`, min in-sync replicas, etc.), Kafka can survive broker or even AZ failures with **no data loss**, at the cost of some throughput and latency.([Cloudurable][2])

### NATS JetStream fault tolerance

JetStream’s approach:

-   Streams are configured with **replication** (e.g., `replicas: 3`)
-   JetStream uses **consensus (Raft)** to replicate stream data across nodes([sobyte.net][5])
-   Consumers track **acks** and handle **redelivery** if a message isn’t processed
-   Clusters and **superclusters** support geo-distribution and failover([widhianbramantya.com][8])

JetStream consumers provide at-least-once delivery via required acks and redelivery if the consumer fails before acknowledging. Exactly-once semantics are available via a combination of deduplication, IDs, and consumer tracking, but come with the usual caveats around idempotent processing.([docs.nats.io][10])

### Durability tradeoffs in practice

-   Kafka is exceptional for **long-term** retention—keeping events for weeks or months, replaying from the beginning of time.([Instaclustr][1])
-   JetStream can also keep data for long periods, but many teams use it more as:

    -   “Keep a rolling window”
    -   “Ensure we don’t drop messages during brief outages”
    -   “Allow replay for debugging or short-term analytics”([docs.nats.io][4])

If your core requirement is **“I want a system of record log for the entire company,”** Kafka is still the more natural fit. If you want **“fast messaging with safety nets”**, JetStream is very compelling.

---

## 5. Operational Complexity: Day-2 Life

Let’s be honest: this is where a lot of teams feel Kafka pain.

### Kafka ops

Running Kafka well in production typically involves:([Instaclustr][1])

-   Multiple brokers + KRaft controllers (or ZooKeeper in older clusters)
-   JVM tuning, heap sizing, garbage collection tuning
-   Disk layout for log segments, retention, compaction
-   Monitoring lag, under-replicated partitions, rebalance storms
-   Optional extras: Kafka Connect, Schema Registry, Kafka Streams, MirrorMaker

Resource-wise, Kafka clusters often start at several GB RAM per broker. Benchmarks and practical guides frequently show Kafka in the 8–16 GB RAM range per node for serious workloads.([My blog][9])

It’s powerful, but it **demands** operational expertise.

### NATS ops

NATS, by design, is much “lighter” to run:([GitHub][3])

-   Single small `nats-server` binary
-   Simple config (port, clustering, JetStream store dir, limits)
-   Mesh-style clustering (servers form a cluster, clients connect to any)
-   JetStream built-in—no extra sidecar processes

NATS servers commonly run happily with a few hundred MB to a GB of RAM for many microservice workloads, compared to multiple GBs for Kafka.([My blog][9])

Operationally:

-   You still need **monitoring** (NATS exposes Prometheus metrics; JetStream has its own monitoring tooling).([Onidel Cloud][7])
-   You still need **backups**, capacity planning, etc.
-   But there are _fewer moving pieces_—no separate metadata service, no JVM, no sidecar ecosystem to keep in sync.

From teams that have written about it publicly, a common theme is: NATS is easier to spin up, scale, and keep healthy as the messaging backbone for microservices.([Brokee][11])

---

## 6. Hands-On: Porting a Kafka-Based Service to NATS

Let’s make this concrete.

Imagine you have a **User Service** that:

-   Publishes `user.created` events
-   Consumes `user.email.updated` events

You’re currently using Kafka; you want to see what this looks like in NATS + JetStream.

We’ll use **Go** for both examples, because NATS itself is written in Go and Kafka’s Sarama client is popular in Go-based systems.([GitHub][12])

> Note: Code below is intentionally simplified and omits robust error handling and configuration. Don’t copy–paste to prod without wrapping it properly.

### 6.1 Kafka version (Sarama, simplified)

First, a minimal Kafka producer that emits `user.created` events:

```go
// kafka_user_created_producer.go
package main

import (
    "encoding/json"
    "log"
    "os"
    "time"

    "github.com/IBM/sarama"
)

type UserCreated struct {
    ID    string `json:"id"`
    Email string `json:"email"`
}

func main() {
    brokers := []string{"localhost:9092"}
    topic := "user-created"

    cfg := sarama.NewConfig()
    cfg.Producer.RequiredAcks = sarama.WaitForAll
    cfg.Producer.Idempotent = true
    cfg.Producer.Return.Successes = true
    cfg.Version = sarama.V3_5_0_0 // example; match your cluster

    producer, err := sarama.NewSyncProducer(brokers, cfg)
    if err != nil {
        log.Fatalf("failed to create producer: %v", err)
    }
    defer producer.Close()

    user := UserCreated{
        ID:    "u-" + time.Now().Format("150405"),
        Email: "user@example.com",
    }

    payload, _ := json.Marshal(user)
    msg := &sarama.ProducerMessage{
        Topic: topic,
        Key:   sarama.StringEncoder(user.ID),
        Value: sarama.ByteEncoder(payload),
    }

    partition, offset, err := producer.SendMessage(msg)
    if err != nil {
        log.Fatalf("failed to send message: %v", err)
    }

    log.Printf("sent to %s[%d]@%d", topic, partition, offset)
    _ = os.Stdout
}
```

Now a simple Kafka consumer group that listens for `user.email.updated`:

```go
// kafka_email_updated_consumer.go
package main

import (
    "context"
    "log"

    "github.com/IBM/sarama"
)

type emailHandler struct{}

func (h *emailHandler) Setup(sarama.ConsumerGroupSession) error   { return nil }
func (h *emailHandler) Cleanup(sarama.ConsumerGroupSession) error { return nil }

func (h *emailHandler) ConsumeClaim(
    sess sarama.ConsumerGroupSession,
    claim sarama.ConsumerGroupClaim,
) error {
    for msg := range claim.Messages() {
        log.Printf("got message: key=%s value=%s", string(msg.Key), string(msg.Value))
        // process…
        sess.MarkMessage(msg, "")
    }
    return nil
}

func main() {
    brokers := []string{"localhost:9092"}
    groupID := "user-email-updated-consumers"
    topics := []string{"user-email-updated"}

    cfg := sarama.NewConfig()
    cfg.Version = sarama.V3_5_0_0
    cfg.Consumer.Group.Rebalance.Strategy = sarama.BalanceStrategyRange

    group, err := sarama.NewConsumerGroup(brokers, groupID, cfg)
    if err != nil {
        log.Fatalf("failed to start consumer group: %v", err)
    }
    defer group.Close()

    ctx := context.Background()
    handler := &emailHandler{}

    for {
        if err := group.Consume(ctx, topics, handler); err != nil {
            log.Printf("consume error: %v", err)
        }
    }
}
```

You get strong guarantees, offsets, consumer groups—but there’s also a fair amount of wiring and config.

### 6.2 NATS + JetStream version

Now, let’s express the same behavior using NATS + JetStream.

#### Step 1: Define a stream

You can create a stream via the `nats` CLI or programmatically. Here’s a minimal config idea (CLI-ish):

```bash
nats str add USERS \
  --subjects "user.*" \
  --storage file \
  --retention limits \
  --max-msgs 100000 \
  --replicas 3
```

This sets up a JetStream stream named `USERS` that stores all subjects starting with `user.` with file-backed, replicated storage.([docs.nats.io][4])

#### Step 2: NATS producer (`user.created`)

```go
// nats_user_created_publisher.go
package main

import (
    "encoding/json"
    "log"
    "time"

    "github.com/nats-io/nats.go"
    "github.com/nats-io/nats.go/jetstream"
)

type UserCreated struct {
    ID    string `json:"id"`
    Email string `json:"email"`
}

func main() {
    nc, err := nats.Connect("nats://localhost:4222")
    if err != nil {
        log.Fatalf("connect: %v", err)
    }
    defer nc.Drain()

    js, err := jetstream.New(nc)
    if err != nil {
        log.Fatalf("jetstream: %v", err)
    }

    user := UserCreated{
        ID:    "u-" + time.Now().Format("150405"),
        Email: "user@example.com",
    }

    payload, _ := json.Marshal(user)

    // Publish to subject that matches the USERS stream
    ack, err := js.Publish("user.created", payload)
    if err != nil {
        log.Fatalf("publish: %v", err)
    }

    log.Printf("stored in stream=%s seq=%d", ack.Stream, ack.Sequence)
}
```

Notice:

-   No explicit partitioning logic
-   JetStream handles persistence, replication, and sequencing within the `USERS` stream

The `jetstream` Go package gives a clearer API for managing streams and consumers than the older embedded JetStream APIs.([GitHub][13])

#### Step 3: NATS consumer (`user.email.updated`)

We’ll use a **durable pull consumer** so we control flow and get at-least-once delivery.

```go
// nats_email_updated_consumer.go
package main

import (
    "context"
    "log"
    "time"

    "github.com/nats-io/nats.go"
    "github.com/nats-io/nats.go/jetstream"
)

func main() {
    nc, err := nats.Connect("nats://localhost:4222")
    if err != nil {
        log.Fatalf("connect: %v", err)
    }
    defer nc.Drain()

    js, err := jetstream.New(nc)
    if err != nil {
        log.Fatalf("jetstream: %v", err)
    }

    // Ensure we have a consumer on the USERS stream for user.email.updated
    consumer, err := js.CreateOrUpdateConsumer(context.Background(), "USERS", jetstream.ConsumerConfig{
        Name:        "email-updated-worker",
        Durable:     "email-updated-worker",
        FilterSubject: "user.email.updated",
        AckPolicy:   jetstream.AckExplicitPolicy,
    })
    if err != nil {
        log.Fatalf("create consumer: %v", err)
    }

    sub, err := consumer.Messages()
    if err != nil {
        log.Fatalf("subscribe: %v", err)
    }
    defer sub.Stop()

    for {
        msg, err := sub.Next()
        if err != nil {
            log.Printf("next error: %v", err)
            time.Sleep(time.Second)
            continue
        }

        log.Printf("got message: subject=%s data=%s", msg.Subject(), string(msg.Data()))

        // process…

        if err := msg.Ack(); err != nil {
            log.Printf("ack error: %v", err)
        }
    }
}
```

Key differences from Kafka:

-   **Filtering is by subject** (`FilterSubject: "user.email.updated"`), not partition
-   The **consumer state** (sequence, acks, redeliveries) is tracked by JetStream
-   Scaling out is as simple as running more instances of this consumer with the same durable/queue group config (JetStream load-balances).([natsbyexample.com][14])

### Swapping out the backing system

If you compare the Kafka and NATS code side-by-side:

-   Producer code is similar in complexity (connect, serialize, send).
-   Consumer code in Kafka leans heavily on **consumer groups** and offsets.
-   Consumer code in JetStream leans on **subjects + consumers + acks**.

For an internal microservice that just wants “don’t drop messages, retry if necessary,” JetStream’s model often feels more direct and less config-heavy than Kafka’s consumer groups—especially as you add cross-region deployments or fine-grained subject filters.

---

## 7. When Less Is More (and When It Isn’t)

So should you drop Kafka tomorrow and YOLO into NATS?

Probably not. The more realistic outcomes look like this.

### Use NATS (+ JetStream) when…

-   You’re building **microservices** that need:

    -   low-latency pub/sub
    -   request–reply
    -   fan-out and queue groups

-   You care a lot about **operational simplicity**—small teams, small clusters
-   You can treat NATS as your **“service mesh for messages”**
-   Your durability needs are about:

    -   surviving node failures
    -   smoothing over brief outages
    -   **short-to-medium** retention + replay([docs.nats.io][4])

### Keep Kafka (or adopt it) when…

-   You’re building **company-wide event streams**: clickstreams, logs, metrics
-   You need **long-term event retention** as a system of record
-   You rely on:

    -   **Kafka Connect** for hundreds of connectors into DBs, S3, etc.
    -   **Kafka Streams** or similar for complex stream processing

-   You’re already invested in Kafka tooling and expertise, and it’s working fine.([Instaclustr][1])

### The hybrid pattern (very common)

A lot of teams end up with:

-   **NATS** as the **internal messaging fabric** for microservices
-   **Kafka** as the **analytical/event backbone** feeding warehouses, lakes, and batch/stream jobs

Events can flow from NATS → Kafka via a bridge (or vice versa), letting each system do what it does best.([Brokee][11])

In that world, “less is more” doesn’t mean eliminating Kafka; it means not forcing **every** problem to look like “publish a message to a giant distributed log.”

---

## 8. Key Takeaways

Let’s compress the journey:

-   **Architecture**

    -   Kafka: distributed, durable commit log with partitions and consumer groups
    -   NATS + JetStream: lightweight messaging fabric with opt-in persistence via streams and consumers

-   **Latency & Throughput**

    -   Kafka: phenomenal throughput; typical P99s in tens of ms under real durability settings
    -   NATS: ultra-low latency for core messaging; JetStream adds persistence with only a small latency bump

-   **Fault Tolerance**

    -   Both rely on **replication + consensus** (KRaft for Kafka, Raft-style for JetStream) to survive node failures
    -   Kafka is better suited as a **long-term system of record**
    -   JetStream excels as a **fault-tolerant message fabric** with replay

-   **Operational Complexity**

    -   Kafka: powerful but heavy—multiple daemons, JVMs, lots of configuration and tuning
    -   NATS: single small binary, simpler clustering, fewer knobs, easier to run in Kubernetes and small environments

-   **Developer Experience**

    -   Kafka: more ceremony; you think in topics, partitions, and offsets
    -   NATS: you think in subjects, request–reply, and streams/consumers when you need durability

If your team is drowning in complexity for workloads that don’t actually need Kafka’s full power, **NATS (and especially NATS + JetStream)** is worth serious exploration.

“From Kafka to NATS” doesn’t have to be an all-or-nothing migration. It can be a gradual, tactical decision:

> “This part of the system wants a fast, simple messaging fabric. Let’s use NATS there, and keep Kafka for the massive data firehose.”

---

## 9. Further Reading & References

If you want to go deeper, these are solid starting points:

-   **Kafka architecture & KRaft**

    -   Cloudurable – _Kafka Architecture – 2025 Edition_([Cloudurable][2])
    -   Instaclustr – _Apache Kafka architecture: A complete guide [2025]_([Instaclustr][1])

-   **NATS & JetStream**

    -   Official NATS docs – _JetStream_ and _Compare NATS_([docs.nats.io][4])
    -   NATS Architecture & JetStream Architecture docs([GitHub][3])
    -   NATS by Example – JetStream examples in Go([natsbyexample.com][15])

-   **Comparisons & Benchmarks**

    -   sanj.dev – _NATS vs Apache Kafka vs RabbitMQ: Messaging Showdown_([My blog][9])
    -   Onidel – _NATS JetStream vs RabbitMQ vs Apache Kafka on VPS in 2025_([Onidel Cloud][7])
    -   Synadia – _NATS and Kafka Compared_([Synadia][16])
    -   AutoMQ – _Apache Kafka vs. NATS: Differences & Comparison_([AutoMQ][17])

[1]: https://www.instaclustr.com/education/apache-kafka/apache-kafka-architecture-a-complete-guide-2025/ "Apache Kafka® architecture: A complete guide [2025]"
[2]: https://cloudurable.com/blog/kafka-architecture-2025/ "Kafka Architecture - 2025 Edition"
[3]: https://github.com/nats-io/nats-general/blob/master/architecture/ARCHITECTURE.md "nats-general/architecture/ARCHITECTURE.md at main · nats-io/nats-general · GitHub"
[4]: https://docs.nats.io/nats-concepts/jetstream "JetStream | NATS Docs"
[5]: https://www.sobyte.net/post/2022-02/nats-server-usage/?utm_source=thinhdanggroup.github.io "Comparison of NATS-Server (JetStream) and NATS Streaming Server"
[6]: https://docs.nats.io/nats-concepts/overview/compare-nats "Compare NATS | NATS Docs"
[7]: https://onidel.com/nats-jetstream-rabbitmq-kafka-2025-benchmarks/ "NATS JetStream vs RabbitMQ vs Apache Kafka on VPS in 2025: Throughput/Latency Benchmarks, Exactly‑Once vs At‑Least‑Once, Durability/Replication, TLS/mTLS, and the Best Message Broker for Your Stack - Onidel Cloud"
[8]: https://widhianbramantya.com/nats/scalability-and-reliability-in-nats/ "Scalability and Reliability in NATS – Widhian Bramantya"
[9]: https://sanj.dev/post/nats-kafka-rabbitmq-messaging-comparison "NATS vs Apache Kafka vs RabbitMQ: Messaging Showdown |
sanj.dev"
[10]: https://docs.nats.io/nats-concepts/jetstream/consumers?utm_source=thinhdanggroup.github.io "Consumers | NATS Docs"
[11]: https://brokee.io/blog/integrating-nats-jetstream-modernizing-internal-communication?utm_source=thinhdanggroup.github.io "Integrating NATS and JetStream: Modernizing Our Internal Communication"
[12]: https://github.com/nats-io/nats.go?utm_source=thinhdanggroup.github.io "GitHub - nats-io/nats.go: Golang client for NATS, the cloud native ..."
[13]: https://github.com/nats-io/nats.go/blob/main/jetstream/README.md?utm_source=thinhdanggroup.github.io "nats.go/jetstream/README.md at main · nats-io/nats.go · GitHub"
[14]: https://natsbyexample.com/examples/jetstream/pull-consumer/go/?utm_source=thinhdanggroup.github.io "NATS by Example - Pull Consumers (Go)"
[15]: https://natsbyexample.com/examples/jetstream/api-migration/go?utm_source=thinhdanggroup.github.io "NATS by Example - Migration to new JetStream API (Go)"
[16]: https://www.synadia.com/blog/nats-and-kafka-compared "NATS and Kafka Compared | Synadia"
[17]: https://www.automq.com/blog/apache-kafka-vs-nats-differences-amp-comparison "Apache Kafka vs. NATS: Differences & Comparison"
