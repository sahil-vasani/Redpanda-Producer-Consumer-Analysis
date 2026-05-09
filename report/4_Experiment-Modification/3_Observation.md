# Observations

## Experiment 1: Impact of Message Size Limits in Redpanda

### Before Changes

| Message Size | Received | Status     |
|--------------|----------|------------|
| 512 KB       | 20 / 20  | ✅ Success |
| 1100 KB      | 0 / 20   | ❌ Rejected |

**Observation:** Large messages are rejected due to default system limits (~1MB).

---

### After Changes

| Message Size | Received | Status     |
|--------------|----------|------------|
| 512 KB       | 20 / 20  | ✅ Success |
| 1100 KB      | 20 / 20  | ✅ Success |

**Observation:** After increasing limits in both producer and broker, large messages are successfully processed.

---

### Key Insight

> Message size limits exist at **multiple layers** in distributed systems.

- Even if the broker allows large messages, the **producer must also allow sending them**.
- Both layers must be configured correctly to support large data.

---

## Experiment 2: Duplicate Message Detection in Redpanda

### Results

1. **New messages are accepted:**
   ```
   ✅ NEW KEY ACCEPTED: key='id_1'
   ✅ NEW KEY ACCEPTED: key='id_2'
   ```

2. **Duplicate messages are detected and skipped:**
   ```
   🚫 DUPLICATE SKIPPED: key='id_1'
   🚫 DUPLICATE SKIPPED: key='id_2'
   ```

3. System correctly distinguishes between:
   - First occurrence → **stored**
   - Repeated occurrence → **rejected**

4. Logs confirm that duplicate detection logic is working at the broker level.

---

### Key Insight

> This experiment shows that:

- Kafka/Redpanda does **not** prevent duplicates by default
- Duplicate handling requires additional logic (like idempotency or custom filtering)
- Broker-level modification can control **data quality before storage**
- Message keys can be used as a simple identifier for duplicate detection

# Observation and Result — Experiment 3

## Hot Partition Problem

---

## Before Source-Code Modification

Before modifying `produce.cc`, Redpanda used **default hash partitioning**. Messages with different keys were automatically distributed across multiple partitions.

**Observed output:**

```
PARTITION=1 KEY=user_3
PARTITION=2 KEY=user_1
PARTITION=0 KEY=user_5
```

Traffic was balanced and consumers processed data from different partitions **in parallel** — this is the expected, healthy behavior of a distributed streaming system.

---

## After Source-Code Modification

After modifying `produce.cc`, broker routing behavior was changed so that all incoming messages were **redirected to partition 0**.

**Observed output:**

```
PARTITION=0 KEY=user_3
PARTITION=0 KEY=user_2
PARTITION=0 KEY=user_1
```

Even though message keys were different, every message was written into the **same partition**.

---

## Hot Partition Successfully Reproduced

The modification successfully reproduced the **Hot Partition Problem**.

**Main observations:**

- One partition became overloaded
- Other partitions remained mostly idle
- Traffic distribution became uneven
- Consumer workload concentrated on a single partition
- Distributed scalability was reduced

---

## Key Takeaway

This experiment proved that **poor partition routing can create bottlenecks even when multiple partitions exist**.

It also demonstrated why real streaming systems must carefully balance:

- Ordering guarantees
- Scalability
- Load balancing
- Consumer throughput

---

## Real-World Parallels

The experiment closely matches real production problems seen in:

| Company | Scenario |
|---|---|
| **Uber** | Surge traffic concentrating on a single trip-id partition |
| **IPL Live Streaming** | Millions of concurrent events routing to one partition |
| **Twitter / X** | Viral tweet events flooding a single shard |
| **Netflix** | Celebrity stream spikes overwhelming one user-id partition |
| **Swiggy** | High-volume restaurants generating disproportionate order events |

These are not edge cases — they are real incidents that have caused outages and degraded consumer experiences at scale. Designing partition strategies that anticipate hotspots is a critical part of production streaming architecture.