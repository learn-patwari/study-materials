# Redis — Senior Engineer Interview Preparation (10–15 YOE)

> Companies that ask deep Redis questions: Amazon, Google, Uber, Flipkart, PhonePe, Razorpay,
> Atlassian, Zomato, LinkedIn, Twitter/X, Shopify, JP Morgan, Goldman Sachs

---

## 1. Redis Internals — How It Really Works

### Q1. Redis is single-threaded. How does it handle thousands of concurrent connections without blocking?

**Answer:**

Redis uses an **event-driven, non-blocking I/O loop** built on `ae` (Async Events), its own abstraction over `epoll` (Linux), `kqueue` (macOS), or `select`.

```
       Client connections (thousands)
              │
              ▼
         ae event loop
       ┌─────────────────────────────┐
       │  epoll_wait() / kqueue      │  ← waits for I/O events
       │     ↓  FD ready?            │
       │  Read command from socket   │
       │  Parse command              │
       │  Execute (in-memory, fast)  │
       │  Write response to socket   │
       └─────────────────────────────┘
```

Key insight: Redis never blocks on I/O. It registers file descriptors and responds only when data is ready. The actual command execution (in-memory hash table lookup, set operation) is sub-microsecond, so a single thread can process **1M+ operations/second**.

**Why single-threaded is an advantage:**
- Zero lock contention — no mutex, no deadlock, no context switching
- Data structures are always in consistent state (no partial writes)
- Deterministic latency (no GC pauses unlike Java caches)

**What IS multi-threaded in Redis 6+:**
- I/O threads (reading from sockets, writing responses) — configurable via `io-threads`
- Background threads: `bio_close_file`, `bio_aof_fsync`, `bio_lazy_free`
- Command execution itself remains single-threaded (the "main" thread)

**Production gotcha:** A slow O(N) command like `KEYS *` on a 10M key instance will block ALL other operations for hundreds of milliseconds. This is the most common Redis performance disaster in production.

---

### Q2. What is the internal data structure Redis uses for each type? Why does it matter?

**Answer:**

Redis uses **encoding-aware dual representations** — it picks the compact encoding for small sizes and switches to the efficient encoding as data grows.

| Type | Small encoding | Large encoding | Switch threshold |
|---|---|---|---|
| String | embstr (≤44 bytes) | raw (SDS) | 44 bytes |
| Hash | listpack | hashtable | `hash-max-listpack-entries` (128), `hash-max-listpack-value` (64) |
| List | listpack | quicklist (linked list of listpacks) | `list-max-listpack-size` (128) |
| Set | listpack (if all integers) → intset | hashtable | `set-max-intset-entries` (512) |
| ZSet | listpack | skiplist + hashtable | `zset-max-listpack-entries` (128) |

**Why this matters for interviews:**

```
HSET user:1 name "Alice"   # encoding: listpack (fast, cache-friendly, 7x less memory)
# Add 200 fields → auto-converts to hashtable (more memory, but O(1) lookup)
```

**SDS (Simple Dynamic String):** Redis's string is not a C string. SDS stores:
- `len` (actual length)
- `alloc` (allocated space)
- `flags` (encoding type)
- `buf[]` (data)

This gives O(1) `STRLEN`, prevents buffer overflows, and allows binary-safe strings (null bytes embedded).

**Skiplist (for ZSet):** Why not a B-tree? Skiplist gives O(log N) insert/delete/search AND efficient range queries (`ZRANGEBYSCORE`), with simpler implementation. Redis uses a 32-level skiplist with probability 1/4.

**Production gotcha:** If you store 1M user IDs in a ZSet for a leaderboard, `ZADD` is O(log N) — that's fine. But if you mistakenly use a Hash with 1M fields, the internal hashtable needs rehashing at 100% load factor → temporary 2x memory spike. Always benchmark encoding switches.

---

### Q3. How does Redis handle memory — what happens when `maxmemory` is hit?

**Answer:**

Redis tracks memory via its own allocator (usually **jemalloc**). When used memory reaches `maxmemory`, eviction policy kicks in:

| Policy | Behavior | Use case |
|---|---|---|
| `noeviction` | Reject writes, return error | Primary DB, don't lose data |
| `allkeys-lru` | Evict least-recently-used key from all keys | General cache |
| `volatile-lru` | LRU eviction only from keys with TTL | Mixed cache + persistent data |
| `allkeys-lfu` | Evict least-frequently-used (Redis 4+) | Hot/cold access patterns |
| `volatile-lfu` | LFU only from TTL keys | — |
| `allkeys-random` | Evict random key | Rarely useful |
| `volatile-random` | Random eviction from TTL keys | — |
| `volatile-ttl` | Evict TTL key closest to expiry | — |

**LRU approximation:** Redis does NOT maintain a true LRU list (that would cost 8 bytes per key). Instead it samples `maxmemory-samples` (default 5) keys and evicts the least-recently used among those. Increasing samples improves accuracy at CPU cost.

**LFU implementation:** Each key has an 8-bit counter using logarithmic approximation (Morris counter). `lfu-log-factor` controls how fast it saturates. `lfu-decay-time` controls counter decay period.

**Memory fragmentation:** jemalloc may allocate more than requested. Monitor:
```
INFO memory
# mem_allocator_frag_ratio > 1.5 → fragmentation is a problem
# Active defragmentation: activedefrag yes
```

**Production gotcha:** Setting `maxmemory` without a policy defaults to `noeviction`. A single `SET` to a full Redis will return `OOM command not allowed when used memory > maxmemory`. This has taken down production systems. Always set `allkeys-lru` for caches.

---

### Q4. How does Redis expire keys? What is the "lazy expiry" mechanism?

**Answer:**

Redis uses two complementary approaches:

**1. Passive (lazy) expiry:**
When a key is accessed, Redis checks `TTL`. If expired → delete immediately, return nil to client. Zero background overhead but expired keys can linger if never accessed.

**2. Active expiry (probabilistic):**
Every 100ms, Redis samples 20 keys from the set of keys with TTL. If ≥25% of sampled keys are expired, it repeats immediately (up to `hz` cycles/second, default 10). This ensures expired keys don't consume memory indefinitely.

```
hz 10                # default: 10 cycles/second active expiry
dynamic-hz yes       # increase hz when many clients connected
lazyfree-lazy-expire yes  # expire in background (Redis 4+)
```

**The expiry is not guaranteed to be exact:**
- `SET key value EX 1` — key may live 1–2 seconds before active sweep removes it
- In a replica, expiry commands are replicated as explicit `DEL` from master (replicas don't independently expire keys — they wait for master's `DEL`)

**Production gotcha:** If you set millions of keys with the same TTL (e.g., cache warmed at startup with `EX 3600`), they all expire simultaneously → **thundering herd** on backend DB. Fix: add random jitter to TTLs.

```java
// Bad: all expire at exactly 3600s
redis.setex(key, 3600, value);

// Good: expire between 3000–3600s
redis.setex(key, 3000 + random.nextInt(600), value);
```

---

## 2. Data Structures — Deep Dive

### Q5. When do you choose String vs Hash for storing a user object?

**Answer:**

**Option A: String (JSON)**
```
SET user:1 '{"name":"Alice","age":30,"email":"alice@example.com"}'
```

**Option B: Hash**
```
HSET user:1 name Alice age 30 email alice@example.com
```

**Comparison:**

| Concern | String (JSON) | Hash |
|---|---|---|
| Read single field | Deserialize full object | `HGET user:1 name` — O(1) |
| Update single field | Read → deserialize → modify → serialize → write | `HSET user:1 age 31` — O(1) |
| Memory (small object) | Same or slightly more | listpack: up to 6x less |
| Memory (large object, 200+ fields) | Depends on JSON size | hashtable: per-field overhead |
| Atomic multi-field update | Not possible without Lua | `HMSET` is a single command |
| TTL | Per-key TTL | Per-key TTL (not per-field) |

**Decision rule:**
- Use **Hash** when you frequently update or read individual fields (user profile, product details, counters per entity)
- Use **String (JSON/Protobuf)** when you always read/write the whole object and never update individual fields

**Key insight for interviews:** Hash with `hash-max-listpack-entries=128` stores up to 128 field-value pairs in a flat listpack (memory-efficient). Beyond that, it switches to hashtable. So for user profiles with <128 fields, Hash is both faster and more memory-efficient than JSON string.

---

### Q6. How does a ZSet (Sorted Set) work internally and when would you use it over alternatives?

**Answer:**

A ZSet stores unique members each with a floating-point score. Internally it uses:
- **skiplist** for O(log N) rank-based and score-range operations
- **hashtable** alongside for O(1) membership test and score lookup

**Why both?** The skiplist knows order but not membership; the hashtable knows membership but not order. Together: `ZSCORE` is O(1) (hashtable), `ZRANGEBYSCORE` is O(log N + M) (skiplist traversal).

**Use cases and commands:**

```bash
# Leaderboard — real-time ranking
ZADD leaderboard 9500 "player:alice"
ZADD leaderboard 8200 "player:bob"
ZREVRANK leaderboard "player:alice"     # rank (0-indexed from top)
ZREVRANGE leaderboard 0 9 WITHSCORES   # top 10

# Rate limiting — sliding window
ZADD req:user:1 1699000001 "uuid1"
ZADD req:user:1 1699000002 "uuid2"
ZREMRANGEBYSCORE req:user:1 0 (now-60)  # remove >60s old
ZCARD req:user:1                         # count in last 60s

# Job scheduling — score = execution timestamp
ZADD delayed_jobs 1699001000 "job:123"
ZRANGEBYSCORE delayed_jobs 0 (now) LIMIT 0 10  # due jobs

# Geospatial (GEOADD uses ZSet internally, score = geohash)
GEOADD locations 77.5946 12.9716 "bangalore"
GEODIST locations "bangalore" "mumbai" km
```

**ZSet vs alternatives:**
- vs List: ZSet has O(log N) insert anywhere; List is O(N) for non-head/tail insert
- vs Set: Set has no ordering; ZSet orders by score
- vs sorted DB column: Redis ZSet is in-memory, orders of magnitude faster for leaderboard reads

---

### Q7. Implement a real-time rate limiter using Redis. Compare Fixed Window vs Sliding Window approaches.

**Answer:**

**Fixed Window Counter:**
```python
def is_allowed_fixed(user_id, limit=100, window_seconds=60):
    key = f"rate:{user_id}:{int(time.time() // window_seconds)}"
    count = redis.incr(key)
    if count == 1:
        redis.expire(key, window_seconds)
    return count <= limit
```

Problem: A user can make 100 requests at second 59 and 100 more at second 61 — 200 requests in 2 seconds despite a "60 second" window.

**Sliding Window Log (ZSet):**
```python
def is_allowed_sliding_log(user_id, limit=100, window_seconds=60):
    now = time.time()
    key = f"rate_log:{user_id}"
    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, 0, now - window_seconds)  # remove old entries
    pipe.zadd(key, {str(uuid.uuid4()): now})             # add current request
    pipe.zcard(key)                                       # count in window
    pipe.expire(key, window_seconds)
    results = pipe.execute()
    count = results[2]
    if count > limit:
        redis.zrem(key, ...)  # remove the just-added entry (deny)
        return False
    return True
```

Accurate but stores one entry per request → memory-heavy for high traffic.

**Sliding Window Counter (best balance):**
```python
def is_allowed_sliding_counter(user_id, limit=100, window_seconds=60):
    now = int(time.time())
    current_window = now // window_seconds
    prev_window = current_window - 1
    elapsed = now % window_seconds
    weight = 1 - (elapsed / window_seconds)  # proportion of previous window

    curr_key = f"rate:{user_id}:{current_window}"
    prev_key = f"rate:{user_id}:{prev_window}"

    pipe = redis.pipeline()
    pipe.get(prev_key)
    pipe.incr(curr_key)
    pipe.expire(curr_key, window_seconds * 2)
    prev_count, curr_count, _ = pipe.execute()

    estimated = (int(prev_count or 0) * weight) + curr_count
    return estimated <= limit
```

This approximates the true sliding window with O(1) space per user — used by Cloudflare, Stripe, and most production systems.

---

### Q8. What is a Redis Stream and how is it different from Pub/Sub and Lists?

**Answer:**

| Feature | Pub/Sub | List (RPUSH/BLPOP) | Stream (XADD/XREAD) |
|---|---|---|---|
| Persistence | No — fire and forget | Yes | Yes |
| Consumer groups | No | No | Yes |
| Message replay | No | No (consumed = gone) | Yes (by ID) |
| Fan-out to multiple consumers | Yes | No (one consumer gets each msg) | Yes (multiple groups) |
| Message ordering | No guarantee | FIFO within list | Guaranteed by ID |
| Backpressure | No | List length limit | MAXLEN option |
| Delivery ACK | No | No | Yes (XACK) |

**Stream commands:**
```bash
# Producer
XADD events * type "order_placed" user_id "123" amount "5000"
# Returns: 1699000001234-0 (millisecond-timestamp + sequence)

# Consumer group
XGROUP CREATE events payment-service $ MKSTREAM

# Consumer reads
XREADGROUP GROUP payment-service consumer-1 COUNT 10 STREAMS events >
# > = only new messages not delivered to any consumer in this group

# Acknowledge
XACK events payment-service 1699000001234-0

# Read pending (unacked) messages — handle crashes
XPENDING events payment-service - + 10
XCLAIM events payment-service consumer-2 30000 1699000001234-0  # take over stale msg
```

**When to use Streams:**
- Exactly-once processing with at-least-once delivery (XACK pattern)
- Event sourcing / audit log (messages persist, replayable)
- Multiple independent consumer groups processing same events
- Replacing Kafka for moderate throughput (<1M events/day) with operational simplicity

**When NOT to use Streams:**
- Simple push notifications → Pub/Sub
- Task queue with single consumer → List (simpler)
- High-throughput event bus (>10M events/day) → Kafka

---

## 3. Persistence

### Q9. RDB vs AOF — which do you choose and when?

**Answer:**

**RDB (Redis Database Backup):**
- Point-in-time snapshot saved as compact binary file
- Uses `fork()` to create child process — child serializes data, parent continues serving
- Default: save after 900 seconds if ≥1 key changed, 300s if ≥10 keys, 60s if ≥10000 keys
- Fast restart (load binary), small file size
- **Data loss:** up to last RDB interval (minutes)

**AOF (Append-Only File):**
- Logs every write command as it happens
- `appendfsync always` — fsync on every write: zero data loss, 1/3 throughput
- `appendfsync everysec` — fsync every second: 1 second max data loss, near-full throughput
- `appendfsync no` — OS decides: best throughput, more data loss risk
- AOF rewrite: Redis forks and rewrites AOF compactly (same data, fewer commands)

**Hybrid persistence (recommended for production):**
```
# redis.conf
appendonly yes
appendfsync everysec
aof-use-rdb-preamble yes    # AOF starts with RDB snapshot, then AOF deltas
# Result: fast load (RDB) + minimal data loss (AOF)
```

**Decision matrix:**

| Scenario | Recommendation |
|---|---|
| Cache only, data loss OK | `save ""` (no persistence) |
| Session store (15-min TTL) | RDB only |
| Primary store, <1s data loss | AOF with `everysec` |
| Financial transactions | AOF with `always` + synchronous replication |
| Fast restart after crash | Hybrid (RDB preamble + AOF) |

**Production gotcha:** `fork()` on a 32 GB Redis instance pauses the process for 1–2 seconds on a heavily fragmented memory system (copy-on-write page table duplication). Monitor `latest_fork_usec` in `INFO stats`. Solutions: use `transparent_hugepage=never`, ensure RAM > 2x data size, or use replica for RDB saves.

---

### Q10. What happens during a Redis fork for RDB save? Explain copy-on-write.

**Answer:**

```
redis-server (parent)              redis-rdb-bgsave (child fork)
       │                                       │
       │  fork() — near-instant copy           │
       │  shares same physical pages ──────────│
       │                                       │
       │  Client writes key A                  │  Serializing key A (old value)
       │  OS copy-on-writes page containing A  │  Still sees old value of A
       │  Parent gets new page                 │
       │  Child still has original page        │  Writes old A to RDB file
       │                                       │
       │  Continue serving requests            │  Finish → rename temp file
```

**Key insight:** In the best case (read-heavy workload), `fork()` is almost free — child shares all parent's memory pages via page table sharing. In the worst case (write-heavy during save), every written page is copied — Redis temporarily needs 2x memory.

**What "copy-on-write" means for memory:**
```
INFO memory
used_memory_rss    # actual RAM consumed by OS (includes COW copies)
used_memory        # Redis's own allocator view

# During active RDB save with write traffic:
# used_memory_rss can spike to 1.5x–2x used_memory
```

**Production impact:** A 10 GB Redis instance under 50% write load during BGSAVE temporarily uses 15 GB RSS. If host has only 12 GB RAM → OOM killer kills Redis. This is one of the most common Redis production incidents.

---

## 4. Replication

### Q11. Explain Redis replication — what happens when a replica connects to a master for the first time vs. reconnects after a brief disconnect?

**Answer:**

**Full Synchronization (first time or too-large gap):**
```
Replica                          Master
   │── PSYNC ? -1 ──────────────▶│  "I don't know my replication ID"
   │                             │  fork → BGSAVE (create RDB)
   │◀── FULLRESYNC <replid> <offset>
   │◀══ RDB stream ══════════════│  (streaming RDB, not saved to disk by default)
   │    (load RDB)               │  buffer write commands during RDB transfer
   │◀── buffered commands ───────│  apply commands after RDB load
   │                             │  now in sync
   │◀── live replication stream  │  every write replicated async
```

**Partial Resynchronization (reconnect within backlog):**
```
Replica                          Master
   │── PSYNC <replid> <offset> ──▶│  "I have replid, last offset N"
   │                              │  check: is offset within repl-backlog?
   │◀── CONTINUE ─────────────────│  send only missing commands from backlog
   │◀── missed commands ──────────│
   │  (no full RDB needed!)       │
```

**Replication backlog** (`repl-backlog-size`, default 1 MB): ring buffer of recent write commands on master. If replica was disconnected longer than backlog covers → full sync needed.

```
repl-backlog-size 256mb    # increase for high-write workloads to avoid full sync
```

**Replication is asynchronous by default:**
```
WAIT numreplicas timeout    # synchronous: block until N replicas ACK
WAIT 1 100                  # wait for 1 replica to confirm, timeout 100ms
```

**Production gotcha:** A replica doing full sync loads a huge RDB while master keeps writing. If the replica falls behind again during load → triggers another full sync → infinite loop. Solution: increase `repl-backlog-size` and ensure replica hardware matches master.

---

### Q12. What is Redis Sentinel? When does it NOT work?

**Answer:**

**Sentinel provides:**
1. **Monitoring:** heartbeats to master and replicas
2. **Automatic failover:** promotes replica to master when master is down
3. **Configuration provider:** clients ask Sentinel for current master address

**Failover process:**
```
1. Sentinel-1 detects master doesn't respond → marks "subjectively down" (SDOWN)
2. Consensus: quorum (e.g., 2 of 3) Sentinels agree → marks "objectively down" (ODOWN)
3. Sentinel leader election (Raft-like vote)
4. Leader: choose best replica (lowest replication lag, highest priority)
5. SLAVEOF NO ONE on chosen replica → becomes new master
6. Update all remaining replicas to replicate from new master
7. Notify clients via Pub/Sub: __sentinel__:hello
```

**When Sentinel FAILS:**
- Network partition where master is still reachable by some clients → **split-brain** (both old master and promoted replica accept writes)
- Sentinel quorum unreachable (all 3 Sentinels in same AZ that went down)
- Client doesn't support Sentinel protocol (doesn't reconnect to new master)
- During failover window (~10–30s), writes to old master are lost

**Split-brain mitigation:**
```
# redis.conf on master
min-replicas-to-write 1       # refuse writes if no replica connected
min-replicas-max-lag 10       # refuse writes if replica lag > 10s
```

**Sentinel vs Cluster:**
- Sentinel: single dataset, multiple replicas, automatic failover — for datasets that fit in one node
- Cluster: sharded dataset across 16384 slots, built-in HA — for datasets too large for one node

---

## 5. Redis Cluster

### Q13. How does Redis Cluster distribute keys? What is a hash slot and what are hash tags?

**Answer:**

Redis Cluster divides the keyspace into **16384 hash slots** (0–16383).

```
slot = CRC16(key) % 16384
```

Each master node owns a contiguous range of slots (typical: 3 masters, ~5461 slots each).

**Routing:**
```
Client → Redis node → if key's slot is local → execute
                    → if slot is remote → MOVED 7638 127.0.0.1:6380 response
                    → client reconnects to correct node
```

Smart clients (Jedis, Lettuce, redis-py-cluster) cache the slot table and route directly, avoiding redirects.

**Hash tags — ensuring co-location:**
```
# Without hash tags: keys go to different slots/nodes
MSET user:1 "alice" order:1:items "..."   # on different nodes — MGET fails!

# With hash tags: only the {} portion is hashed
MSET {user:1}:profile "alice" {user:1}:orders "..."   # same slot guaranteed!
SET {game:room:42}:players "..."
SET {game:room:42}:state "..."
```

**Multi-key commands in Cluster:**
- `MSET`, `MGET`, `SUNION` across different slots → `CROSSSLOT` error
- Must use hash tags to group related keys on same slot
- `EVAL` (Lua) only works if all keys are on same slot

**Resharding (add new node):**
```bash
redis-cli --cluster add-node new_host:port master_host:port
redis-cli --cluster reshard existing_host:port
# Moves slots incrementally — no downtime
```

---

### Q14. What is the CLUSTER MEET / gossip protocol? How does cluster detect node failure?

**Answer:**

**Gossip protocol:**
- Every node sends PING to a random subset of nodes every second
- Pong contains the node's view of the cluster (slot assignments, node states)
- Cluster state converges across nodes via this gossip (eventual consistency)

**Node failure detection:**
```
1. Node A sends PING to Node B, no PONG within cluster-node-timeout/2
2. A marks B as "PFAIL" (probable fail)
3. A gossips its B=PFAIL view to other nodes in PING messages
4. When majority of masters see B=PFAIL → mark B as "FAIL"
5. Failover starts: B's replica campaigns to become master
6. Replica with largest replication offset wins (most up-to-date data)
7. New master takes over B's hash slots
```

**`cluster-node-timeout` (default 15s):**
- Failure detection time ≈ timeout
- Failover completes in 1–2x timeout
- Shorter timeout → faster recovery but more false positives on network jitter

---

## 6. Transactions & Lua Scripting

### Q15. What does MULTI/EXEC actually guarantee? Is it truly ACID?

**Answer:**

Redis transactions with `MULTI`/`EXEC`:

```redis
MULTI
SET balance:1 900
SET balance:2 1100
EXEC
```

**What it guarantees:**
- **Atomicity of queuing:** All commands execute or none (if `EXEC` never called or `DISCARD` used)
- **No interleaving:** No other client command executes between MULTI and EXEC
- **Isolation:** Complete during execution

**What it does NOT guarantee:**
- **No rollback on error:** If `SET balance:1 900` succeeds but the next command fails (e.g., wrong type), the first command is NOT rolled back. Redis only rolls back if a command has a syntax error (caught at queue time).

```redis
MULTI
SET key1 "hello"
INCR key1        # will fail at exec time (wrong type), but SET already committed
EXEC
# returns: [OK, ERR wrong type]
# key1 = "hello" — partial execution!
```

**WATCH — Optimistic Locking (CAS pattern):**
```redis
WATCH balance:user:1
current_balance = GET balance:user:1  # read outside transaction

MULTI
SET balance:user:1 (current_balance - 100)
EXEC
# Returns nil if balance:user:1 changed since WATCH → retry
```

`WATCH` turns MULTI/EXEC into optimistic locking — if watched key changes before EXEC, the entire transaction aborts (returns nil). Client must retry.

**Redis is NOT fully ACID:**
- No Durability guarantee without AOF `always`
- No automatic rollback (no "undo log")
- No isolation levels — only a single isolation level (serialized within EXEC)

**When to use Lua instead:**
```lua
-- Atomic check-and-update — impossible with just MULTI/EXEC safely
local balance = tonumber(redis.call('GET', KEYS[1]))
if balance >= tonumber(ARGV[1]) then
    redis.call('DECRBY', KEYS[1], ARGV[1])
    return 1  -- success
end
return 0  -- insufficient funds
```

Lua scripts are atomic — no client can interleave. Script is cached on server by SHA1 (`EVALSHA`).

---

### Q16. Implement a distributed lock in Redis correctly. What is Redlock and when is it controversial?

**Answer:**

**Basic distributed lock (single node):**
```python
import uuid

def acquire_lock(redis, resource, ttl_ms=10000):
    token = str(uuid.uuid4())
    acquired = redis.set(
        f"lock:{resource}",
        token,
        px=ttl_ms,    # milliseconds TTL
        nx=True       # only set if not exists
    )
    return token if acquired else None

def release_lock(redis, resource, token):
    # Lua script: compare-and-delete (atomic)
    script = """
    if redis.call('get', KEYS[1]) == ARGV[1] then
        return redis.call('del', KEYS[1])
    else
        return 0
    end
    """
    return redis.eval(script, 1, f"lock:{resource}", token)
```

**Critical:** Always use Lua for release — a `GET` + `DEL` without atomicity can delete another client's lock if your TTL expired between the two commands.

**Redlock (for multiple Redis nodes):**

Antirez's algorithm for distributed lock across N (typically 5) independent Redis nodes:
1. Get current timestamp T1
2. Try `SET lock:resource token PX ttl NX` on all N nodes with small timeout
3. Lock acquired if: (a) majority (N/2 + 1) nodes said OK AND (b) elapsed time < TTL
4. Valid lock duration = TTL − elapsed
5. Release: `DEL lock:resource` on all N nodes (with compare-and-delete Lua)

**Redlock controversy (Martin Kleppmann's critique):**
- Process GC pause between acquiring lock and using it can violate mutual exclusion
- Network delays can mean "elapsed time" calculation is wrong
- Clock skew across nodes can lead to different TTL calculations
- NTP adjustments can cause TTL to expire unexpectedly

**Redlock is safe for these use cases:**
- Efficiency locks (prevent duplicate expensive work — losing the lock occasionally is OK)
- Not safe for: distributed consensus, exact-once execution without fencing token

**Fencing token pattern (correct solution for safety-critical locks):**
```
Client 1: lock → gets token "42"
Client 1: GC pause for 10s → lock expires
Client 2: lock → gets token "43"
Client 2: writes to storage with token "43"
Client 1: resumes, writes to storage with token "42" → storage REJECTS (42 < 43)
```

---

## 7. Pub/Sub and Messaging

### Q17. Redis Pub/Sub — what are its critical limitations in production?

**Answer:**

```bash
# Publisher
PUBLISH news:breaking "Markets crash 5%"

# Subscriber (different connection)
SUBSCRIBE news:breaking
# Or pattern subscribe
PSUBSCRIBE news:*
```

**Limitations:**

1. **No persistence:** If subscriber is down → messages are lost forever. No replay, no acknowledgment.

2. **No consumer groups:** Every subscriber on a channel gets every message. No load balancing.

3. **No backpressure:** If subscriber is slow, Redis buffers messages up to `client-output-buffer-limit pubsub`. After limit → client disconnected.
```
client-output-buffer-limit pubsub 32mb 8mb 60
# Hard limit: 32MB — disconnect immediately
# Soft limit: 8MB for 60 seconds — then disconnect
```

4. **Blocking subscriber connection:** The subscribed connection can ONLY send `SUBSCRIBE`, `UNSUBSCRIBE`, `PING`. Cannot send regular commands.

5. **No acknowledgment:** Fire-and-forget. You never know if the subscriber received the message.

**When Pub/Sub IS appropriate:**
- Real-time notifications where occasional loss is acceptable (chat presence, live dashboard refresh)
- Cache invalidation signals (losing a signal means stale cache, not data corruption)
- Simple fan-out where all subscribers are always online

**Replace Pub/Sub with Streams when:**
- Messages must not be lost
- Need consumer groups (load balancing)
- Need message replay
- Need delivery acknowledgment

---

## 8. Common Patterns (Most Asked in System Design Rounds)

### Q18. Design a session store in Redis. What TTL strategy do you use?

**Answer:**

```python
import json, uuid

def create_session(user_id, session_data, ttl_seconds=1800):
    session_id = str(uuid.uuid4())
    key = f"session:{session_id}"
    # Hash: efficient for partial reads/writes
    redis.hset(key, mapping={
        "user_id": user_id,
        "created_at": int(time.time()),
        **session_data
    })
    redis.expire(key, ttl_seconds)
    return session_id

def touch_session(session_id, ttl_seconds=1800):
    # Sliding expiry: extend TTL on every request
    redis.expire(f"session:{session_id}", ttl_seconds)

def get_session(session_id):
    data = redis.hgetall(f"session:{session_id}")
    if not data:
        return None  # expired or invalid
    touch_session(session_id)  # sliding window
    return data

def invalidate_session(session_id):
    redis.delete(f"session:{session_id}")
```

**TTL strategies:**

| Strategy | Implementation | Use case |
|---|---|---|
| Fixed TTL | `EXPIRE key 1800` once at creation | Simple, predictable expiry |
| Sliding window | `EXPIRE key 1800` on every access | "Session expires after 30 min of inactivity" |
| Absolute deadline | Store `expires_at` in session data, check in app | Legal/compliance max session time |
| Hybrid | Sliding + absolute cap | "Active sessions expire after 8 hours max" |

**All-user session invalidation (logout all devices):**
```python
# Strategy 1: Store sessions in Set per user
def login(user_id, session_id):
    redis.sadd(f"user_sessions:{user_id}", session_id)

def logout_all(user_id):
    sessions = redis.smembers(f"user_sessions:{user_id}")
    pipe = redis.pipeline()
    for s in sessions:
        pipe.delete(f"session:{s}")
    pipe.delete(f"user_sessions:{user_id}")
    pipe.execute()

# Strategy 2: Version token in session
def is_session_valid(session_id, user_id):
    session = get_session(session_id)
    current_version = redis.get(f"session_version:{user_id}")
    return session.get("version") == current_version

def logout_all(user_id):
    redis.incr(f"session_version:{user_id}")  # invalidates all sessions instantly
```

---

### Q19. Design a Redis-based leaderboard that supports real-time ranking, top-N queries, and rank of a specific user.

**Answer:**

```python
# Update score
ZADD leaderboard:game:1 9500 "user:alice"
ZADD leaderboard:game:1 8200 "user:bob"
ZADD leaderboard:game:1 9500 "user:charlie"  # tie with alice

# Get top 10
ZREVRANGE leaderboard:game:1 0 9 WITHSCORES
# → [(user:alice, 9500), (user:charlie, 9500), (user:bob, 8200)]

# Get rank (0-indexed)
ZREVRANK leaderboard:game:1 "user:bob"
# → 2 (third place)

# Score of specific user
ZSCORE leaderboard:game:1 "user:alice"

# Add to score (increment)
ZINCRBY leaderboard:game:1 500 "user:bob"
# → 8700.0

# Get users in score range
ZRANGEBYSCORE leaderboard:game:1 8000 9000 WITHSCORES

# Count users above a threshold
ZCOUNT leaderboard:game:1 9000 +inf
```

**Handling ties (lexicographic ordering):**
```python
# Score = primary_score * 1e10 + (MAX_TIME - timestamp)
# Ensures same-score users ordered by who got there first
def encode_score(score, timestamp):
    return score * 10_000_000_000 + (9_999_999_999 - timestamp)
```

**Weekly leaderboard (auto-expiring):**
```python
def get_leaderboard_key():
    week = datetime.now().strftime("%Y-W%W")
    return f"leaderboard:{week}"

def update_score(user_id, delta):
    key = get_leaderboard_key()
    redis.zincrby(key, delta, f"user:{user_id}")
    redis.expire(key, 7 * 24 * 3600)  # 7 days TTL
```

**Near-me leaderboard (friends only):**
```python
# Intersection of friends set with global leaderboard
ZINTERSTORE friends_leaderboard:alice 2 leaderboard:game:1 friends:alice WEIGHTS 1 0
# friends:alice is a set (score=1 for each friend)
# WEIGHTS 1 0 → use leaderboard score, ignore friends set score
```

---

### Q20. How do you implement a job queue with Redis that supports delayed jobs, priority, and at-least-once delivery?

**Answer:**

**Simple job queue (List):**
```python
# Producer
def enqueue(queue, job_data):
    redis.rpush(f"queue:{queue}", json.dumps(job_data))

# Consumer (blocking, 0 = wait forever)
def dequeue(queue, timeout=0):
    result = redis.blpop(f"queue:{queue}", timeout=timeout)
    return json.loads(result[1]) if result else None
```

**Priority queue (multiple lists):**
```python
QUEUES = ["queue:critical", "queue:high", "queue:normal", "queue:low"]

def dequeue_priority(timeout=1):
    result = redis.blpop(QUEUES, timeout=timeout)  # checks left-to-right priority
    return result
```

**Delayed jobs (ZSet as scheduler):**
```python
def schedule_job(job_data, run_at_timestamp):
    redis.zadd("delayed_jobs", {json.dumps(job_data): run_at_timestamp})

def poll_due_jobs():
    now = time.time()
    # Atomically pop jobs due now
    script = """
    local jobs = redis.call('ZRANGEBYSCORE', KEYS[1], 0, ARGV[1], 'LIMIT', 0, 10)
    if #jobs > 0 then
        redis.call('ZREM', KEYS[1], unpack(jobs))
        return jobs
    end
    return {}
    """
    jobs = redis.eval(script, 1, "delayed_jobs", now)
    for job in jobs:
        redis.rpush("queue:normal", job)
```

**At-least-once delivery (reliable queue pattern):**
```python
def reliable_dequeue(queue, processing_set, timeout_seconds=300):
    # Move from queue to processing set atomically
    job = redis.rpoplpush(f"queue:{queue}", f"processing:{queue}")
    if job:
        # Store with timestamp to detect stale processing
        redis.zadd(f"processing_times:{queue}", {job: time.time()})
    return job

def acknowledge(queue, job):
    redis.lrem(f"processing:{queue}", 1, job)
    redis.zrem(f"processing_times:{queue}", job)

def recover_stale_jobs(queue, stale_after_seconds=300):
    cutoff = time.time() - stale_after_seconds
    stale = redis.zrangebyscore(f"processing_times:{queue}", 0, cutoff)
    for job in stale:
        redis.lrem(f"processing:{queue}", 1, job)
        redis.zrem(f"processing_times:{queue}", job)
        redis.rpush(f"queue:{queue}", job)  # re-enqueue
```

---

## 9. Memory Optimization

### Q21. How do you reduce Redis memory usage by 10x for a large dataset?

**Answer:**

**1. Use appropriate data structures (biggest impact):**
```python
# Bad: one key per user field (N keys, N separate metadata overheads)
SET user:1:name "Alice"        # ~96 bytes overhead each
SET user:1:age "30"
SET user:1:email "alice@x.com"

# Good: single Hash per user (1 key, listpack encoding for <128 fields)
HSET user:1 name Alice age 30 email alice@x.com
# Memory: ~40 bytes total for same data
```

**2. Use integer encoding:**
```python
# Redis detects integer strings and stores as 64-bit int (8 bytes vs 20+ bytes)
SET counter 1234567890    # stored as integer, not string
```

**3. Tune encoding thresholds:**
```
# Increase before data hits threshold to keep compact encoding longer
hash-max-listpack-entries 256   # default 128
hash-max-listpack-value 128     # default 64
zset-max-listpack-entries 256
list-max-listpack-size 256
```

**4. Compress values at application level:**
```python
import zlib, msgpack

def store_compressed(redis, key, data):
    serialized = msgpack.packb(data)        # 3-5x smaller than JSON
    compressed = zlib.compress(serialized)   # additional 2-5x compression
    redis.set(key, compressed)

def load_compressed(redis, key):
    compressed = redis.get(key)
    return msgpack.unpackb(zlib.decompress(compressed))
```

**5. Use short key names (not just for memory, but for performance):**
```
# Bad: 40+ byte key
user:profile:1234567:preferences

# Good: 15 byte key
u:1234567:pref
```

**6. Monitor per-datatype memory:**
```bash
redis-cli --memkeys    # top-N keys by memory usage
redis-cli object encoding mykey  # check current encoding
redis-cli debug object mykey     # serializedlength shows compressed size
```

**7. Shared integers pool:** Redis pre-allocates integers 0–9999 as shared objects. `INCR counter` with value in this range costs 0 additional bytes.

---

## 10. Performance Tuning

### Q22. What commands should never be used in production? What are the O(N) dangers?

**Answer:**

**Never use in production on large datasets:**

| Command | Why dangerous | Safe alternative |
|---|---|---|
| `KEYS *` | O(N) scans all keys, blocks Redis | `SCAN 0 COUNT 100` (cursor-based, non-blocking) |
| `SMEMBERS` on huge set | Returns entire set | `SSCAN`, process in chunks |
| `HGETALL` on huge hash | Returns all fields | `HSCAN`, `HMGET` specific fields |
| `LRANGE key 0 -1` on huge list | Returns entire list | Paginate with `LRANGE key 0 99` |
| `SORT` without `LIMIT` | Sorts entire list/set | `SORT key LIMIT 0 10` |
| `SUNIONSTORE` on huge sets | Creates big intermediate set | Batch processing |
| `FLUSHALL` / `FLUSHDB` | Synchronous, blocks for seconds | `FLUSHDB ASYNC` (Redis 4+) |
| `DEBUG SLEEP` | Deliberately blocks | Don't use outside testing |
| `OBJECT ENCODING` + loop | Each call is fine; looping is not | `SCAN` + sample |

**Safe SCAN pattern:**
```python
def scan_all_keys(pattern="*"):
    cursor = 0
    while True:
        cursor, keys = redis.scan(cursor, match=pattern, count=100)
        for key in keys:
            yield key
        if cursor == 0:
            break
```

**Pipeline to reduce RTT:**
```python
# Bad: 1000 round trips
for user_id in user_ids:
    redis.get(f"user:{user_id}")

# Good: 1 round trip for 1000 GETs
pipe = redis.pipeline(transaction=False)
for user_id in user_ids:
    pipe.get(f"user:{user_id}")
results = pipe.execute()
```

**`transaction=False` on pipeline:** Disables MULTI/EXEC wrapping — commands are still batched but not atomic. Use for read batches to avoid unnecessary server overhead.

---

### Q23. How do you debug a slow Redis command? Walk through your production debugging process.

**Answer:**

**Step 1: Enable slowlog**
```bash
CONFIG SET slowlog-log-slower-than 10000  # 10ms threshold (microseconds)
CONFIG SET slowlog-max-len 128

SLOWLOG GET 10   # top 10 slowest commands
# Returns: [id, timestamp, duration_us, [command, args...], client_ip, client_name]
```

**Step 2: Monitor live commands**
```bash
MONITOR   # prints every command in real time — USE ONLY BRIEFLY, 50% CPU overhead
# Alternatively:
redis-cli --latency      # measure round-trip latency
redis-cli --latency-hist # histogram
redis-cli --stat         # live stats every second
```

**Step 3: Check INFO for hotspots**
```bash
INFO commandstats
# cmdstat_hgetall:calls=1000000,usec=50000000,usec_per_call=50.00
# → HGETALL averaging 50 microseconds → investigate key size
```

**Step 4: Identify big keys**
```bash
redis-cli --bigkeys      # scans all keys, reports largest by type
# Warning: uses SCAN internally, safe but slow on large instances
```

**Step 5: Check for blocking commands**
```bash
CLIENT LIST              # see all connected clients and their current command
# Look for: cmd=eval, cmd=sort, cmd=keys with large datasets
```

**Step 6: Latency monitoring (Redis built-in)**
```bash
CONFIG SET latency-monitor-threshold 100  # events > 100ms
LATENCY LATEST           # most recent latency event per event type
LATENCY HISTORY event    # history for specific event type
LATENCY RESET            # clear history
```

---

## 11. High Availability Patterns

### Q24. How do you implement cache-aside with cache stampede prevention?

**Answer:**

**Cache-aside (lazy loading) — basic:**
```python
def get_user(user_id):
    key = f"user:{user_id}"
    cached = redis.get(key)
    if cached:
        return json.loads(cached)
    
    # Cache miss — load from DB
    user = db.query("SELECT * FROM users WHERE id = ?", user_id)
    redis.setex(key, 3600, json.dumps(user))
    return user
```

**Problem: Cache stampede (thundering herd)**

When a popular key expires, hundreds of threads simultaneously miss the cache, all hit the DB, all write the same value back.

**Solution 1: Mutex / lock on cache miss**
```python
def get_user_safe(user_id):
    key = f"user:{user_id}"
    lock_key = f"lock:populating:{key}"
    
    cached = redis.get(key)
    if cached:
        return json.loads(cached)
    
    # Try to acquire lock
    lock_acquired = redis.set(lock_key, "1", nx=True, ex=5)
    if lock_acquired:
        try:
            user = db.query("SELECT * FROM users WHERE id = ?", user_id)
            redis.setex(key, 3600, json.dumps(user))
            return user
        finally:
            redis.delete(lock_key)
    else:
        # Another thread is populating — wait briefly and retry
        time.sleep(0.1)
        return get_user_safe(user_id)  # retry
```

**Solution 2: Probabilistic early expiry (XFetch)**
```python
import math, random

def get_with_early_expiry(key, ttl, fetch_fn, beta=1.0):
    data = redis.get(key)
    if data:
        value, stored_at, delta = json.loads(data)
        # Check if we should proactively refresh
        time_to_expire = (stored_at + ttl) - time.time()
        if time_to_expire - beta * delta * math.log(random.random()) < 0:
            # Probabilistically decided to refresh early
            t_start = time.time()
            value = fetch_fn()
            delta = time.time() - t_start
            redis.setex(key, ttl, json.dumps([value, time.time(), delta]))
        return value
    
    # Full miss
    t_start = time.time()
    value = fetch_fn()
    delta = time.time() - t_start
    redis.setex(key, ttl, json.dumps([value, time.time(), delta]))
    return value
```

**Solution 3: Stale-while-revalidate**
```python
def get_with_stale(key, ttl, stale_ttl, fetch_fn):
    # Store: {data, compute_time}; key expires at ttl, stale version at stale_ttl
    data = redis.get(key)
    stale = redis.get(f"stale:{key}")
    
    if data:
        return json.loads(data)
    elif stale:
        # Return stale immediately, refresh in background
        if not redis.set(f"lock:{key}", "1", nx=True, ex=10):
            return json.loads(stale)  # lock held by another refresher
        threading.Thread(target=refresh, args=(key, ttl, stale_ttl, fetch_fn)).start()
        return json.loads(stale)
    else:
        return refresh(key, ttl, stale_ttl, fetch_fn)
```

---

## 12. Real Interview Questions by Company

### Q25. Amazon/Flipkart: Design a flash sale system where only 1000 units are available and 100,000 users hit buy simultaneously.

**Answer:**

```python
# Initialize inventory as Redis counter
redis.set("sale:product:1:stock", 1000)

def purchase(user_id, product_id):
    # Atomic decrement — returns new value
    remaining = redis.decr(f"sale:product:{product_id}:stock")
    
    if remaining < 0:
        # Compensate: we over-decremented
        redis.incr(f"sale:product:{product_id}:stock")
        return {"status": "SOLD_OUT"}
    
    # Record purchase (async — don't block user)
    redis.rpush("purchase_queue", json.dumps({
        "user_id": user_id,
        "product_id": product_id,
        "timestamp": time.time()
    }))
    
    return {"status": "SUCCESS", "remaining": max(0, remaining)}
```

**Why this works:**
- `DECR` is atomic — no two users can both get the same remaining count
- When remaining hits -1 → exactly the 1001st user gets SOLD_OUT
- Actual DB writes are async via queue

**Preventing duplicate purchases:**
```python
def purchase_once(user_id, product_id):
    # Check if user already bought
    if redis.sismember(f"sale:buyers:{product_id}", user_id):
        return {"status": "ALREADY_PURCHASED"}
    
    # Lua script: atomic check-decrement-record
    script = """
    local bought = redis.call('SISMEMBER', KEYS[1], ARGV[1])
    if bought == 1 then return -1 end
    local remaining = redis.call('DECR', KEYS[2])
    if remaining < 0 then
        redis.call('INCR', KEYS[2])
        return -2
    end
    redis.call('SADD', KEYS[1], ARGV[1])
    redis.call('EXPIRE', KEYS[1], 86400)
    return remaining
    """
    result = redis.eval(script, 2, 
                        f"sale:buyers:{product_id}",
                        f"sale:product:{product_id}:stock",
                        user_id)
    if result == -1: return {"status": "ALREADY_PURCHASED"}
    if result == -2: return {"status": "SOLD_OUT"}
    return {"status": "SUCCESS", "remaining": result}
```

---

### Q26. Uber/Lyft: Design a "nearby drivers" feature using Redis. How do you update and query positions efficiently?

**Answer:**

Redis **GEO commands** use a ZSet internally with geohash as score.

```python
# Driver updates position every 5 seconds
def update_driver_position(driver_id, latitude, longitude):
    redis.geoadd("drivers:active", longitude, latitude, f"driver:{driver_id}")
    # Also update driver metadata
    redis.hset(f"driver:{driver_id}", mapping={
        "lat": latitude, "lon": longitude, "updated_at": int(time.time())
    })
    redis.expire(f"driver:{driver_id}", 30)  # remove stale drivers

# Find drivers within 5km
def find_nearby_drivers(latitude, longitude, radius_km=5, count=10):
    results = redis.georadius(
        "drivers:active",
        longitude, latitude,
        radius_km, "km",
        withcoord=True,
        withdist=True,
        count=count,
        sort="ASC"
    )
    # Modern alternative: GEOSEARCH (Redis 6.2+)
    results = redis.geosearch(
        "drivers:active",
        longitude=longitude, latitude=latitude,
        radius=radius_km, unit="km",
        withcoord=True, withdist=True, count=count, sort="ASC"
    )
    return [{"driver_id": r[0], "distance_km": r[1]} for r in results]

# Remove driver (goes offline)
def driver_offline(driver_id):
    redis.zrem("drivers:active", f"driver:{driver_id}")
```

**Scale considerations:**
- 100,000 active drivers → single ZSet is ~8 MB (fine for one node)
- 1M drivers → shard by city: `drivers:active:bangalore`, `drivers:active:delhi`
- GEO precision: geohash level 6 ≈ 1.2 km accuracy (sufficient for "nearby")

**Surge pricing zones:**
```python
# Check if location is in surge zone
def get_surge_multiplier(lat, lon):
    zones = redis.georadius("surge:zones", lon, lat, 2, "km", count=1)
    if zones:
        return float(redis.hget("surge:multiplier", zones[0]))
    return 1.0
```

---

### Q27. Goldman Sachs/JP Morgan: How do you use Redis for real-time market data feed? What are the consistency concerns?

**Answer:**

```python
# Publish tick data
def publish_tick(symbol, price, volume, timestamp):
    tick = {"price": price, "volume": volume, "ts": timestamp}
    
    # Latest price (String — overwrite with each tick)
    redis.set(f"tick:{symbol}:latest", json.dumps(tick))
    
    # OHLCV per minute (Hash)
    minute_key = f"ohlcv:{symbol}:{timestamp // 60}"
    pipe = redis.pipeline()
    pipe.hsetnx(minute_key, "open", price)   # only first price of minute
    pipe.hset(minute_key, "close", price)    # always update close
    pipe.hset(minute_key, "volume", redis.hincrbyfloat(minute_key, "volume", volume))
    # High/Low — Lua for atomic compare
    pipe.execute()
    
    # Stream for subscribers (persistent, replayable)
    redis.xadd(f"stream:ticks:{symbol}", {"*": json.dumps(tick)},
               maxlen=10000, approximate=True)

# Subscribe to feed
def consume_ticks(symbol, last_id="0-0"):
    while True:
        messages = redis.xread({f"stream:ticks:{symbol}": last_id}, count=100, block=100)
        for stream, msgs in (messages or []):
            for msg_id, data in msgs:
                process_tick(data)
                last_id = msg_id
```

**Consistency concerns:**

1. **Redis is eventually consistent with replicas** — tick published to master may not yet be on replica when subscriber reads from replica
2. **No transactions across symbols** — you cannot atomically update AAPL and its index SPX
3. **Pub/Sub drops ticks** if subscriber is slow — use Streams with ACK for guaranteed delivery
4. **Clock skew** — timestamp from publisher may not match server time; always use application-provided timestamp, not `TIME` command
5. **AOF not appropriate for tick data** — millions of ticks/sec, AOF overhead unbearable; keep Redis as L1 cache, write to TimescaleDB/InfluxDB asynchronously

---

## 13. Redis vs Alternatives

### Q28. When would you NOT use Redis? What are its weaknesses?

**Answer:**

**Don't use Redis when:**

| Scenario | Better alternative |
|---|---|
| Dataset > available RAM | Memcached (eviction-focused), disk-backed cache (Apache Ignite), or Cassandra |
| Complex queries on cached data | PostgreSQL with connection pooling + read replicas |
| ACID transactions across multiple entities | PostgreSQL, CockroachDB |
| High-durability event streaming (10M+ events/day) | Apache Kafka |
| Full-text search on cached data | Elasticsearch |
| Graph traversal | Neo4j |
| Column analytics on cached data | ClickHouse |
| Multi-region active-active with strong consistency | CockroachDB, Spanner |

**Redis weaknesses:**
- **Memory cost:** RAM is expensive. 100M objects at 100 bytes each = 10 GB RAM minimum
- **No query language:** No equivalent of SQL WHERE on arbitrary fields
- **Single-region by default:** Redis Cluster doesn't natively span multiple regions with active-active writes
- **No secondary indexes:** Must build them manually (maintain a separate index key)
- **Cluster resharding complexity:** Moving slots affects all keys in that slot
- **Persistence overhead:** AOF `always` costs 3x write throughput; RDB causes periodic fork pauses

**Redis Enterprise vs open-source for enterprise needs:**
- Active-Active geo-replication (CRDT-based conflict resolution)
- RediSearch (secondary indexes, full-text search)
- RedisJSON (native JSON with path queries)
- RedisGraph, RedisTimeSeries
- Automatic sharding and failover without Cluster config complexity

---

## 14. Rapid Fire — Frequently Asked One-Liners

**Q: What is the maximum size of a Redis value?**
512 MB (any type). Practical limit for Strings — never store anything > a few MB; it blocks I/O on read/write.

**Q: What happens if you INCR a key that doesn't exist?**
Redis creates it with value 0 and increments to 1. Atomically.

**Q: Can Redis store null values?**
No. A key either exists with a value or doesn't exist. `GET nonexistent` returns nil (not null).

**Q: Difference between DEL and UNLINK?**
`DEL` is synchronous — blocks while deleting. `UNLINK` unlinks the key immediately (O(1)) and deletes data in background thread. Use `UNLINK` for large keys.

**Q: What is WAIT command?**
`WAIT numreplicas timeout` — blocks until N replicas acknowledge the latest write, with timeout. Used to add sync replication semantics when needed.

**Q: What is the output of `SET key value EX 100 XX`?**
Sets key with 100s TTL **only if the key already exists** (`XX` = only if eXists). Returns OK or nil.

**Q: Why does `EXPIRE key -1` not work in older Redis?**
`EXPIRE` requires positive integer. Use `PERSIST key` to remove TTL. Redis 7.0 added `EXPIRE key 0` support (immediately expires).

**Q: What is object encoding for an empty list?**
There is no empty list. As soon as all elements are removed, the key is deleted.

**Q: Can two clients both successfully `SETNX key value` simultaneously?**
No. `SETNX` is atomic. Exactly one will get OK, the other gets 0.

**Q: What does `DEBUG OBJECT key` tell you?**
Shows: encoding, refcount, serializedlength (compressed size), lru_seconds_idle.

**Q: What is CLIENT NO-EVICT and CLIENT NO-TOUCH?**
`CLIENT NO-EVICT on` — prevents this client's connection from being closed under memory pressure.  
`CLIENT NO-TOUCH on` — commands from this client don't update LRU/LFU counters (useful for analytics reads that shouldn't affect eviction).

**Q: How does OBJECT FREQ work?**
Returns the logarithmic access frequency counter for a key (only meaningful with LFU eviction policy).

**Q: Difference between `redis.pipeline()` and `redis.pipeline(transaction=True)`?**
`transaction=True` (default) wraps commands in `MULTI`/`EXEC` → atomic. `transaction=False` batches commands for network efficiency without atomicity guarantee.

**Q: What is the `hz` config?**
Number of times Redis's timer interrupt fires per second (default 10). Controls: active key expiry frequency, lazy free, client timeout checks. Higher hz = more responsive expiry but more CPU.

**Q: Can you do a conditional set based on current value atomically without Lua?**
No. You need Lua or `WATCH`/`MULTI`/`EXEC` (optimistic lock). There is no `SET key value IF_VALUE_EQUALS old_value` command.

---

## 15. System Design Integration (Putting It All Together)

### Q29. You're designing BookMyShow's seat reservation. Walk through the Redis components end-to-end.

**Answer:**

```
User selects seats → Redis lock per seat → payment → commit to DB → release lock
```

**1. Seat availability (read path):**
```python
# Bitmap: 1 bit per seat, 0=available, 1=booked
# For show 123 with 500 seats: 500 bits = 63 bytes
SETBIT show:123:seats 42 0   # seat 42 available
SETBIT show:123:seats 43 1   # seat 43 booked

# Get status of seat 42
GETBIT show:123:seats 42     # → 0 (available)

# Count available seats
BITCOUNT show:123:seats      # → count of 1 bits = booked seats
# available = total_seats - booked
```

**2. Seat reservation (write path — prevent double booking):**
```python
def reserve_seats(show_id, seat_ids, user_id, ttl=600):
    pipe = redis.pipeline()
    for seat_id in seat_ids:
        key = f"seat_lock:{show_id}:{seat_id}"
        pipe.set(key, user_id, ex=ttl, nx=True)  # NX = only if not exists
    results = pipe.execute()
    
    if all(results):
        return True  # all seats locked for this user
    else:
        # Rollback: release any seats we did lock
        to_release = [seat_ids[i] for i, r in enumerate(results) if r]
        release_seats(show_id, to_release, user_id)
        return False  # one or more seats already taken

def release_seats(show_id, seat_ids, user_id):
    # Only release if we own the lock
    for seat_id in seat_ids:
        key = f"seat_lock:{show_id}:{seat_id}"
        release_lock_script = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        end
        return 0
        """
        redis.eval(release_lock_script, 1, key, user_id)
```

**3. Show listing cache (read-heavy):**
```python
# Cache show listing with 5-minute TTL
redis.setex(f"shows:city:{city_id}", 300, json.dumps(shows))

# Cache seat map per show with 30-second TTL (changes as seats are booked)
redis.setex(f"show_seats:{show_id}", 30, json.dumps(seat_map))
```

**4. Pub/Sub for real-time seat availability UI:**
```python
# When seat is reserved/released, publish event
redis.publish(f"show:{show_id}:seats", json.dumps({
    "type": "reserved", "seat_id": seat_id, "user": user_id
}))

# Frontend WebSocket handler subscribes and updates UI in real time
```

**5. Booking stats (counters):**
```python
redis.incr(f"show:{show_id}:bookings_today")
redis.incrby(f"show:{show_id}:revenue_today", amount)
```

This architecture handles:
- 100,000 concurrent users browsing shows → Redis bitmap reads
- 10,000 simultaneous seat selections → NX locks prevent double booking
- Zero double-booking guarantee → atomic NX operations
- Auto-release of abandoned selections → TTL on lock keys
