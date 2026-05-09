# Why These Experiments?

## Experiment 1: Impact of Message Size Limits in Redpanda (Producer + Broker)

In real-world systems like banking, trading, or e-commerce, messages can become large (e.g., transaction data, images, logs).

By default, streaming systems like Redpanda/Kafka have size limits. If a message exceeds this limit, it is rejected.

This experiment is done to understand:
1. Where large messages are blocked (producer or broker)
2. How system behavior changes when limits are increased
3. How to safely support larger messages in production systems

### Real-Life Example

Imagine a courier system:

**Truck (Producer)** → carries packages  
**Warehouse (Broker)** → accepts packages

**Before:**
- Truck capacity = 1 ton
- Warehouse capacity = 1 ton
- If package = 1.1 ton → rejected ❌

**After:**
- Truck capacity = 5 ton
- Warehouse capacity = 5 ton
- Same package → delivered successfully ✅

---

## Experiment 2: Duplicate Message Detection in Redpanda

In distributed streaming systems like Redpanda/Kafka, duplicate messages can occur due to retries, network issues, or producer behavior.

By default, the broker does not prevent duplicate messages, which can lead to incorrect data processing in downstream systems.

The goal of this experiment is to modify the Redpanda broker (C++ source code) to:
1. Detect duplicate messages using message keys
2. Log duplicate occurrences

This helps us understand how duplicate handling can be implemented at the broker level and its impact on system behavior.

# Experiment 3 — Hot Partition Problem

## Hash Key → Round-Robin

---

## Why Hash Partitioning Exists

Modern streaming systems like Kafka and Redpanda use hash partitioning:

```
hash(key) % number_of_partitions
```

This means the **same key always goes to the same partition**. Companies use this because event order is important.

---

## Real-Life Example

Swiggy / Zomato use `order_id` as the partition key, so events remain ordered:

```
order_created
food_prepared
delivery_started
delivered
```

This is critical — if events go randomly, food may appear `"delivered"` before `"prepared"`.

Similarly:

- **Banking** uses `account_id`
- **Uber** uses `trip_id`
- **Netflix** uses `user_id`

---

## The Hot Partition Problem

Hash partitioning creates a real problem called:

```
HOT PARTITION PROBLEM
```

Suppose one key becomes extremely popular:

```
IPL_FINAL
celebrity_stream
viral_restaurant
```

Now **millions of events go to the same partition**.

---

## Consequences of a Hot Partition

- Consumer lag increases
- One broker shard becomes overloaded 
- Slow analytics and degraded throughput

---

## Solutions Used in Production

To solve this problem, some streaming systems use:

- **Round-robin routing** — cycles through partitions evenly
- **Random partitioning** — spreads traffic without any key affinity
- **Dynamic routing** — adjusts based on real-time load

This improves load balancing because traffic spreads across partitions instead of concentrating in one place.

---

## When Round-Robin / Random Partitioning Is Used

Round-robin and random partitioning are commonly used in:

- Server logs
- Monitoring systems
- Telemetry pipelines
- Clickstream analytics

...because **strict ordering is less important than scalability and throughput** in these use cases.

---

## The Core Tradeoff

This experiment demonstrates the fundamental tradeoff between:

| Approach | Benefit | Cost |
|---|---|---|
| **Hash partitioning** | Ordering guarantees | Risk of hot partitions |
| **Round-robin / Random** | Scalability and load balancing | No per-key ordering |

Understanding this tradeoff is essential for designing high-throughput, fault-tolerant streaming pipelines.
