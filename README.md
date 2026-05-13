# Redpanda Producer-Consumer Analysis

> Reverse Engineering & Experimental Modification of Redpanda's Core Streaming Engine
> We took Redpanda's C++ source code, modified it, and ran 4 experiments to understand how real streaming systems work internally.

---

## Table of Contents

1. [What is Redpanda?](#what-is-redpanda)
2. [Why Not Just Kafka?](#why-not-just-kafka)
3. [Repository Structure](#repository-structure)
4. [Key Source Files](#key-source-files)
5. [System Requirements](#system-requirements)
6. [Setup & Installation](#setup--installation)
7. [Experiments](#experiments)
8. [Known Failure Cases](#known-failure-cases)
9. [Conclusion](#conclusion)
10. [Authors](#authors)

---

## What is Redpanda?

- **Redpanda** is a real-time event streaming platform — just like Apache Kafka
- It moves data continuously between systems in real time
- Written in **C++** — no Java, no ZooKeeper, no extra tools needed
- Works with any Kafka-compatible client (drop-in replacement)

**Where is it used?**

| Company | Use Case |
|---|---|
| Swiggy / Zomato | Order & delivery event streams |
| Netflix | Watch events, recommendations |
| Uber | Live GPS updates, ride tracking |
| Banking | Transaction events, fraud detection |

**Why do we need streaming at all?**
- Modern apps generate millions of events every second
- Normal databases cannot handle this continuous flow efficiently
- Without streaming → dashboards get delayed, notifications become slow, analytics break

---

## Why Not Just Kafka?

Kafka is popular, but it has real problems at scale. Redpanda was built to fix them.

- Redpanda still supports the Kafka API because millions of applications already use Kafka clients and Kafka-based ecosystems. 
- Companies do not want to rewrite their producer and consumer applications from the beginning So Redpanda keeps Kafka compatibility, meaning:
  Kafka producers can talk to Redpanda 
  Kafka consumers can read from Redpanda 
  existing Kafka tools still work

But internally, Redpanda changes the architecture to solve some practical operational problems companies faced with Kafka.

- One major issue was that Kafka is JVM-based because it is written in Java. 
- In large-scale streaming systems, JVM garbage collection can sometimes pause processing temporarily. 
- Under huge traffic loads, this may increase latency or create performance spikes.


### Problem 1 — ZooKeeper Complexity
- Kafka needs a separate tool called **ZooKeeper** to manage brokers
- If ZooKeeper crashes → broker coordination fails → messages stop flowing
- Example: In a Swiggy-like system, if ZooKeeper goes down, order events pause completely
- **Redpanda fix:** Uses built-in Raft consensus — no ZooKeeper needed at all

### Problem 2 — JVM Garbage Collection Pauses
- Kafka runs on Java (JVM)
- JVM periodically stops everything to clean memory (GC pause)
- Even 200ms pause = delayed notifications, slow ride assignments
- Example: During IPL Finals with millions of events, JVM GC pauses cause visible lag
- **Redpanda fix:** Written in C++ — no garbage collector, no pauses

### Problem 3 — Too Much Infrastructure
- A production Kafka setup needs: Kafka brokers + ZooKeeper + Schema Registry + Kafka Connect + Monitoring tools
- Each component can fail, needs tuning, needs its own team to manage
- **Redpanda fix:** Single binary — one process, one config, far fewer things to break

### Problem 4 — High Latency Under Load
- During traffic spikes (flash sales, live events), Kafka consumers fall behind
- Messages pile up → delayed order tracking, stale app state for users
- **Redpanda fix:** Thread-per-core architecture with `io_uring` for fast async I/O

### Problem 5 — Hard Local Development
- Running Kafka locally = configure Kafka + ZooKeeper + Docker Compose + multiple config files
- Slows down developers, makes onboarding painful
- **Redpanda fix:** Single binary, minimal config — runs on a laptop in minutes

### Quick Comparison

| Kafka Problem | Redpanda Solution |
|---|---|
| Needs ZooKeeper | Raft consensus built-in |
| JVM GC pauses | C++ — no GC |
| Heavy infrastructure | Single binary |
| High latency | io_uring + thread-per-core |
| Hard local setup | Minimal config, fast start |

---
# Redpanda Streaming Flow

```text
Producer → Kafka API Layer → Partition Routing → Raft Consensus → Storage Engine → Replication → Fetch Handler → Consumer
```

---

## Repository Structure

```
Redpanda-Producer-Consumer-Analysis/
│
├── redpanda/                          ← Redpanda original source code (cloned)
│   ├── src/
│   │   └── v/
│   │       └── kafka/
│   │           └── server/
│   │               └── handlers/
│   │                   ├── produce.cc     ← ✏️ Producer handler (we modified this)
│   │                   └── fetch.cc       ← ✏️ Consumer handler (we studied this)
│   │
│   ├── experiment/                    ← All experiment Python scripts
│   │   ├── experiment1_before.py
│   │   ├── experiment1_after.py
│   │   ├── experiment2.py
│   │   ├── experiment3_producer.py
│   │   ├── experiment3_consumer.py
│   │   ├── experiment4_producer.py
│   │   └── experiment4_consumer.py
│   │
│   └── Images/                        ← Screenshots of experiment outputs
│       ├── Experiment1.png
│       ├── Experiment3_before.png
│       ├── Experiment3_after.png
│       ├── Experiment4_producer.png
│       ├── Experiment4_consumer.png
│       └── Experiment4_file.png
│
├── report/
│   ├── 4_Experiment-Modification/
│   │   └── redpanda/
│   ├── 1_why_experiment.md
│   ├── 2_Experiment.md
│   ├── 3_Observation.md
│   ├── 1_Execution Understanding.md
│   ├── 2_Design Decisions.md
│   ├── 3_concept_mapping.md
│   └── 5_Failure-Analysis.md
│
└── README.md
```

---

## Key Source Files

We did **reverse engineering** — we read the original C++ source code, understood how it works, then modified it to run our experiments.

### `produce.cc` — Producer Handler
**Path:** `redpanda/src/v/kafka/server/handlers/produce.cc`

- Runs every time a producer sends a message to Redpanda
- Checks message size, validates the batch, routes to the right partition, writes to storage
- **All 4 experiments involved modifying this file**

### `fetch.cc` — Consumer Handler
**Path:** `redpanda/src/v/kafka/server/handlers/fetch.cc`

- Runs every time a consumer asks Redpanda for messages
- Reads batches from the partition log and returns them to the consumer
- We studied this file to verify that our `produce.cc` changes had the correct downstream effect on consumers

---

## System Requirements

| Component | Requirement |
|---|---|
| Operating System | Ubuntu 22.04 LTS (recommended) |
| CPU | x86-64, 4+ cores recommended |
| RAM | Minimum 8 GB (16 GB recommended for builds) |
| Disk | 20 GB+ free space |
| Build Tool | Bazel 6.x |
| Compiler | Clang 14+ (GCC not supported) |
| Python | Python 3.8+ |
| Python Libraries | `kafka-python`, `confluent-kafka` |

---

## Setup & Installation

### Step 1 — Clone Redpanda Source Code

```bash
git clone https://github.com/redpanda-data/redpanda.git
cd redpanda
```

### Step 2 — Install Redpanda (Pre-built Binary)

```bash
curl -1sLf 'https://dl.redpanda.com/nzc4ZYQK3WRGd9sy/redpanda/cfg/setup/bash.deb.sh' | sudo -E bash
sudo apt-get install redpanda -y
```

### Step 3 — Install Python Libraries

```bash
pip install kafka-python confluent-kafka
```

### Step 4 — Build Redpanda from Source

> Do this after every source code change to compile it into a binary

```bash
bazel build //src/v/redpanda:redpanda \
  --config=release \
  --jobs=2 \
  --local_resources=memory=4096 \
  --define=use_system_liburing=true \
  --action_env=LIBURING_USE_SYSTEM=1 \
  --spawn_strategy=standalone
```

- Output binary will be at: `bazel-bin/src/v/redpanda/redpanda`

### Step 5 — Start the Redpanda Server

```bash
./bazel-bin/src/v/redpanda/redpanda \
  --redpanda-cfg redpanda.yaml \
  --smp=1 \
  --memory=1G \
  --reserve-memory=0M
```

- Leave this terminal open while running experiments
- Server listens on port `9092` (Kafka-compatible)

---

## Experiments

### Where We Made Changes

| Experiment | File Modified | What We Changed |
|---|---|---|
| 1 — Message Size Limits | `produce.cc` | Increased batch size limit by 5× to allow large messages |
| 2 — Duplicate Detection | `produce.cc` | Added logic to detect and reject repeated message keys |
| 3 — Hot Partition Problem | `produce.cc` | Forced all messages to route to partition 0 |
| 4 — Failed Event Storage | `produce.cc` | Extended duplicate detection to save rejected events to a file |

---

### Experiment 1 — Message Size Limits

**Why we did this:**
- Real systems (banking, e-commerce) send large messages — images, logs, transaction blobs
- By default, Redpanda rejects messages above ~1 MB
- We wanted to understand where rejection happens and how to fix it at the source level

**Simple analogy:**
- Courier truck (producer) has a 1-ton weight limit
- Warehouse (broker) also has a 1-ton intake limit
- A 1.1-ton package gets rejected — you must increase BOTH limits

**What we changed in `produce.cc`:**

```cpp
// Original: hard limit check
if (static_cast<uint32_t>(batch_size) > req.batch_max_bytes)

// Modified: allow 5× the default limit
uint32_t custom_max_batch_bytes = req.batch_max_bytes * 5;
if (static_cast<uint32_t>(batch_size) > custom_max_batch_bytes)
```

**Result:**

| Message Size | Before (Received / Sent) | After (Received / Sent) |
|---|---|---|
| 512 KB | 20 / 20 ✅ | 20 / 20 ✅ |
| 1100 KB | 0 / 20 ❌ | 20 / 20 ✅ |

**Key takeaway:**
- Size limits exist at both the producer AND broker layer
- Fixing only one side still causes rejection — both must be updated together

---

### Experiment 2 — Duplicate Message Detection

**Why we did this:**
- Network retries, timeouts, and producer failures can send the same message twice
- Redpanda does NOT filter duplicates by default
- Duplicates in payment systems → double charges; in logistics → double dispatches

**Real example:**
- Swiggy payment service sends `payment_1` for order #1001
- Network timeout → service retries → `payment_1` sent again
- Without filtering → customer gets charged twice

**What we changed in `produce.cc`:**
- Added a `thread_local unordered_set` to remember all message keys seen so far
- If a key appears again → log it and skip writing to storage

```cpp
static thread_local std::unordered_set<ss::sstring> seen_keys;

if (seen_keys.contains(key_str)) {
    vlog(klog.info, "🚫 DUPLICATE SKIPPED: key='{}'", key_str);
    // return without writing to partition log
} else {
    seen_keys.insert(key_str);
    vlog(klog.info, "✅ NEW KEY ACCEPTED: key='{}'", key_str);
}
```

**Result:**

```
✅ NEW KEY ACCEPTED: key='id_1'
✅ NEW KEY ACCEPTED: key='id_2'
🚫 DUPLICATE SKIPPED: key='id_1'
🚫 DUPLICATE SKIPPED: key='id_2'
✅ NEW KEY ACCEPTED: key='id_3'
```

**Key takeaway:**
- Redpanda does not block duplicates by default — you must add this logic yourself
- Broker-level duplicate filtering protects all downstream consumers automatically

---

### Experiment 3 — Hot Partition Problem

**Why we did this:**
- Redpanda uses `hash(key) % num_partitions` to route messages to partitions
- Same key → same partition → keeps messages in order (needed for order tracking)
- But if one key gets millions of events (IPL Final, viral tweet, flash sale) → one partition gets overloaded while others sit idle
- This is the **Hot Partition Problem** — a real production bottleneck

**Real examples:**

| Company | Hot Partition Scenario |
|---|---|
| Uber | Surge traffic flooding one `trip_id` partition |
| IPL Live | Millions of score events going to one partition |
| Twitter / X | Viral tweet flooding a single shard |
| Netflix | Celebrity stream spike hitting one `user_id` partition |
| Swiggy | Popular restaurant generating too many order events |

**What we changed in `produce.cc`:**
- Overrode partition routing to send ALL messages to partition 0
- This artificially created a hot partition so we could observe it directly

```cpp
// Force everything to partition 0 — simulate a hot partition
model::partition_id dynamic_partition(0);
```

**Result — Before (healthy, balanced):**

```
PARTITION=1  KEY=user_3
PARTITION=2  KEY=user_1
PARTITION=0  KEY=user_5
```

**Result — After (hot partition created):**

```
PARTITION=0  KEY=user_3
PARTITION=0  KEY=user_2
PARTITION=0  KEY=user_1
PARTITION=0  KEY=user_5
```

**Key takeaway:**
- One overloaded partition = slower consumers, increased lag, reduced throughput
- Other partitions sit idle even though they could handle traffic
- Solutions used in production: round-robin routing, random partitioning, load-aware routing

---

### Experiment 4 — Duplicate & Failed Event Storage

**Why we did this:**
- In Experiment 2, we silently dropped duplicate messages — they just disappeared
- In production, silent drops are dangerous — no audit trail, no way to retry, no recovery
- We extended the duplicate detection to save rejected events to `failed_events.avro`
- This simulates the **Dead Letter Queue (DLQ)** pattern used in real streaming systems

**Real example:**
- Swiggy payment service sends `payment_1` twice due to network retry
- Without storage → duplicate is dropped silently, impossible to debug
- With storage → duplicate is saved, can be retried or audited later

**What we changed in `produce.cc`:**
- Added a file write inside the duplicate detection block before dropping the event

```cpp
if (seen_keys.contains(key_str)) {

    // Write to lightweight retry file before dropping
    std::ofstream retry_file("failed_events.avro", std::ios::app | std::ios::binary);
    retry_file << "{"
               << "\"event_type\":\"DUPLICATE\","
               << "\"key\":\"" << key_str << "\","
               << "\"topic\":\"" << req.ntp.tp.topic() << "\""
               << "}" << std::endl;
    retry_file.close();

    co_return finalize_request_with_error_code(...);
}
```

**Result:**

| State | What Happened |
|---|---|
| Before modification | Consumer received `payment_1` twice — duplicate passed through |
| After modification | Consumer received only unique events — duplicates removed from main stream |
| Failed event file | `failed_events.avro` created automatically with all rejected events |

**Contents of `failed_events.avro` after run:**

```json
{"event_type":"DUPLICATE","key":"payment_1","topic":"retry-topic"}
{"event_type":"DUPLICATE","key":"payment_2","topic":"retry-topic"}
```

**Key takeaway:**
- Never silently drop events in production — always store them somewhere safe
- Lightweight file-based storage keeps costs low compared to a full DLQ setup
- Stored events can be retried, audited, or used for debugging at any time

---

## Known Failure Cases

These are real failure modes in production Redpanda / Kafka deployments — not edge cases. Several have caused actual outages.

### 1 — Broker Unavailability
- **What happens:** A broker node crashes due to memory/CPU exhaustion or network issues
- **Error seen:** `broker_not_available`
- **Real example:** During IPL Finals, a Redpanda node runs out of memory → producers get connection errors → live score updates stop → users see stale scoreboards
- **Fix:** Run multiple broker nodes; set proper replication; monitor memory and CPU

### 2 — Disk Space Exhaustion
- **What happens:** Redpanda writes an append-only log — if disk fills up, the broker halts completely and stops accepting messages
- **Real example:** An e-commerce clickstream pipeline has no log retention policy → during a Diwali sale, disk fills up in hours → broker stops → upstream producers overflow their local queues too
- **Fix:** Set log retention limits (`retention.bytes`, `retention.ms`); monitor disk usage actively

### 3 — Under-Replicated Partitions
- **What happens:** A broker node fails → remaining replicas fall below the replication factor → partitions become under-replicated → producers with `acks=all` start timing out
- **Real example:** A ride-hailing app loses one broker node during evening peak → GPS location events stop flowing → dispatch system cannot assign rides → customers wait with no updates
- **Fix:** Set replication factor ≥ 3; alert immediately when under-replicated partition count > 0

### 4 — Memory / OOM Crash
- **What happens:** OS kills the Redpanda process due to out-of-memory → broker may not restart cleanly → requires [Recovery Mode](https://docs.redpanda.com/current/manage/recovery-mode/) before rejoining the cluster
- **Real example:** A financial pipeline suddenly receives large end-of-day settlement batches → Redpanda node is OOM-killed → in-flight settlement transactions are interrupted → manual recovery needed before the broker can resume
- **Fix:** Set `--memory` flag appropriately; always set `--reserve-memory` to protect the OS; monitor resident memory

---

## Conclusion

**What this project proved:**
- Streaming systems like Redpanda are not black boxes — their internal behaviour can be understood and modified at the source level
- Message size limits exist at multiple layers — producer and broker must both be configured together
- Broker-level duplicate detection is not built-in — it requires custom logic, but once added it protects all downstream consumers automatically
- The Hot Partition Problem is a real and measurable bottleneck — it can be reproduced in a lab and solved with smarter routing strategies
- Silent event drops are dangerous in production — lightweight retry storage solves this without the cost of a full DLQ setup

**Core tradeoff in streaming systems:**

| Approach | Benefit | Cost |
|---|---|---|
| Hash partitioning | Message ordering guaranteed | Risk of hot partitions |
| Round-robin / Random | Balanced load, higher throughput | No per-key ordering |
| Deduplication at broker | Clean data for all consumers | Slight write overhead |
| Retry / DLQ storage | Full auditability and recovery | Extra disk space for failed events |

---

## Authors

**Students**
- Sahil Vasani
- Raj Nakrani

**Mentor**
- Prof. Ankush Chander

---

*Redpanda Source Code: https://github.com/redpanda-data/redpanda*