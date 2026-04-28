# Redpanda Producer–Consumer Analysis

> A Big Data Engineering study — tracing the **producer → broker → consumer** flow inside Redpanda's source code, mapping system design decisions, and analysing real system behaviour through controlled experiments.

---

## What This Project Is

This project is a **source-code-level analysis** of [Redpanda](https://github.com/redpanda-data/redpanda) — a Kafka-API-compatible, high-performance streaming platform written in C++ on top of the Seastar framework.

The goal is **not** to build a new application on top of Redpanda.  
The goal is to **understand how Redpanda itself works internally** by:

- Reading and tracing the actual Redpanda source code
- Mapping system design decisions (architecture choices, trade-offs)
- Running experiments and observing real system behaviour
- Analysing failure scenarios and how the system responds

This is purely a **producer–consumer flow study**. Only two files from Redpanda's source are the entry points for this analysis:

| File | Role |
|------|------|
| `produce.cc` | Handles the **producer path** — how messages enter the broker |
| `fetch.cc` | Handles the **consumer path** — how messages are fetched from the broker |

Everything — design decisions, experiments, observations, failure analysis — is traced through these two files and the subsystems they touch.

---

## Repository Structure

```
Redpanda-Producer-Consumer-Analysis/
│
├── report/
│   ├── 1_introduction.md        # Project background and scope
│   ├── 2_system_design.md       # System design decision mapping
│   ├── 3_observation.md         # Core experiments and observations  ← PRIMARY
│   └── 4_failure_analysis.md    # Failure scenarios derived from observations
│
└── README.md
```

> **Note on experiments:** The experiment and modification section is grounded entirely in `3_observation.md`. Observations from live runs and source-code tracing are the only reliable source — other files are supplementary context.

---

## Core Concepts Studied

### 1. System Design Decision Mapping
Tracing *why* Redpanda makes the architectural choices it does inside the produce and fetch paths:
- Thread-per-core model via Seastar (no shared state, no locks)
- Batching and debouncing write operations (avoids kernel flush overhead)
- No JVM — no GC pauses affecting tail latency
- Direct I/O — bypasses page cache, eliminates kernel file-handler locks
- Raft-based replication per partition

### 2. Producer–Consumer Flow (via `produce.cc` and `fetch.cc`)

```
Producer Client
      │
      ▼
[ produce.cc ]  ←── Entry point for incoming produce requests
      │
      ├── Message size validation
      ├── Batching / compression
      ├── Partition leader resolution
      ├── Raft replication (write quorum)
      └── fsync / commit acknowledgment
              │
              ▼
         [ Log / Disk ]
              │
              ▼
[ fetch.cc ]  ←── Entry point for consumer fetch requests
      │
      ├── Offset tracking
      ├── Partition read
      └── Response assembly
              │
              ▼
      Consumer Client
```

### 3. Experiments & Observations (`3_observation.md`)

The heart of the project. All experiments are run against Redpanda's actual produce and fetch paths. Only `3_observation.md` is used as the basis for the experiment/modification section because it contains concrete, reproducible results — other report files are harder to interpret in isolation.

---

## Experiments

### Experiment 1 — Impact of Message Size Limits in Redpanda

This experiment studies what happens when messages exceed Redpanda's default size limits, and what changes are needed at both the producer and broker layers to support large messages.

#### Before Changes

| Message Size | Received  | Status      |
|--------------|-----------|-------------|
| 512 KB       | 20 / 20   | ✅ Success  |
| 1100 KB      | 0 / 20    | ❌ Rejected |

**Observation:** Large messages are rejected due to default system limits (~1 MB).

#### After Changes

| Message Size | Received  | Status      |
|--------------|-----------|-------------|
| 512 KB       | 20 / 20   | ✅ Success  |
| 1100 KB      | 20 / 20   | ✅ Success  |

**Observation:** After increasing limits in both the producer and broker, large messages are successfully processed.

#### Key Insight

- Message size limits exist at **multiple layers** in a distributed system — the producer and the broker are independent enforcement points.
- Even if the broker allows large messages, the producer must also be configured to send them.
- **Both layers must be configured correctly** to support large payloads.
- This reflects a general principle in big data engineering: system-level configuration must be consistent across all components in the pipeline.

---

### Experiment 2 — Duplicate Message Detection in Redpanda

This experiment studies how Redpanda handles repeated messages with the same key, and how broker-level logic can be used to enforce data quality.

#### Results

New messages are accepted:
```
✅ NEW KEY ACCEPTED: key='id_1'
✅ NEW KEY ACCEPTED: key='id_2'
```

Duplicate messages are detected and skipped:
```
🚫 DUPLICATE SKIPPED: key='id_1'
🚫 DUPLICATE SKIPPED: key='id_2'
```

The system correctly distinguishes between:
- **First occurrence** → stored
- **Repeated occurrence** → rejected

Logs confirm that duplicate detection logic is working at the broker level.

#### Key Insight

- Kafka/Redpanda does **not** prevent duplicates by default.
- Duplicate handling requires additional logic — such as idempotency settings or custom broker-level filtering.
- **Broker-level modification can control data quality before storage** — enforcing deduplication at the source rather than downstream.
- Message keys can serve as a simple, effective identifier for duplicate detection in the produce path.

---

## What We Do NOT Cover

- Redpanda administration or cluster setup tutorials
- Kafka client compatibility testing
- Transforms / WASM engine
- Schema Registry or Redpanda Console
- Any language-level client (Python, Go, Java) usage

This study stays at the **C++ source code level**, focused only on the produce and fetch paths.

---

## Key Source Files in Redpanda (Referenced)

These files are from the [official Redpanda repository](https://github.com/redpanda-data/redpanda):

| File | Path in Redpanda source |
|------|-------------------------|
| `produce.cc` | `src/v/kafka/server/handlers/produce.cc` |
| `fetch.cc` | `src/v/kafka/server/handlers/fetch.cc` |

All analysis, design decisions, and experiments in this repo are anchored to these two files.

---

## Report Index

| # | File | Description |
|---|------|-------------|
| 1 | `1_introduction.md` | Project scope, motivation, what Redpanda is |
| 2 | `2_system_design.md` | Architecture decisions traced through source code |
| **3** | **`3_observation.md`** | **Experiments, traces, real observations ← Start here** |
| 4 | `4_failure_analysis.md` | Failure modes derived from `3_observation.md` |

---

## Why Redpanda?

Redpanda is a ground-up rewrite of a Kafka-compatible broker in C++ focused on:
- **Predictable low latency** — no JVM, no GC pauses
- **No ZooKeeper** — Raft consensus is built in
- **Thread-per-core** — each CPU core owns its data, zero contention
- **Direct I/O** — no page cache, no kernel lock overhead

Studying its produce and fetch paths gives deep insight into how a modern, high-performance distributed streaming system is actually engineered at the source level.

---

## Author

Sahil Vasani
Raj Nakrani

---

