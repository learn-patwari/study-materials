[← Round 1](Round-1-Hiring-Manager.md) · [Role index](README.md) · [Next: Round 3 →](Round-3-Coding-and-Machine-Coding.md)

# Round 2 — DSA + Design

> **Format:** A problem-solving round mixing **data structures & algorithms** with a lighter
> **design** discussion. At Staff level they care less about you memorizing exotic algorithms and
> more about: clean problem decomposition, correct complexity analysis, edge cases, readable
> code, and communicating as you go. Expect 1–2 DSA problems, possibly followed by "now how would
> you scale this / design the system around it."

---

## How to run a DSA problem (say this process out loud)

1. **Clarify** — inputs, outputs, constraints, sizes, edge cases. Restate the problem.
2. **Examples** — walk one concrete example, including an edge case.
3. **Brute force first** — state it and its complexity; don't code it.
4. **Optimize** — identify the bottleneck, pick the data structure/pattern that removes it.
5. **Code** — clean, named variables, small helpers. Narrate.
6. **Test** — dry-run the example + edges (empty, single, duplicates, overflow, nulls).
7. **Complexity** — state final time & space, and any trade-offs.

> 💡 Staff signal: proactively discuss trade-offs and "what changes if input is 10⁹ / streaming /
> concurrent." That bridges DSA into design.

---

## Priority patterns (given an API-platform team)

Focus your practice here — these recur and map to platform work (caching, routing, rate limiting,
dedup, streaming):

| Pattern | Why it matters here | Classic problems |
|---------|--------------------|------------------|
| **Hashing / HashMap** | Routing tables, dedup, counting | Two Sum, Group Anagrams, Subarray Sum = K |
| **Sliding window** | Rate limiting, stream windows | Longest Substring w/o Repeat, Min Window Substring, Max in window |
| **Two pointers** | Array/string processing | 3Sum, Container With Most Water, dedup sorted |
| **Heap / priority queue** | Top-K APIs, scheduling | Top K Frequent, Merge K Sorted Lists, task scheduler |
| **LinkedList + Hash (LRU)** | **Caches** (core to the role) | **LRU Cache**, LFU Cache |
| **Trees / Tries** | Path routing, prefix match | Trie (implement), Word Search, LCA |
| **Graphs / BFS-DFS / Topo sort** | Dependency resolution, service graphs | Course Schedule, Clone Graph, Number of Islands |
| **Intervals** | Rate/quota windows, scheduling | Merge Intervals, Meeting Rooms II |
| **Binary search** | Rate/threshold tuning | Search Rotated, Koko Eating Bananas, min-capacity |
| **Design DS** | Direct machine-coding overlap | LRU, Rate Limiter, HashMap, Snapshot, TimeMap |

**If you optimize your time:** master **LRU/LFU cache**, **sliding-window rate limiting**,
**Top-K with heaps**, **Trie for routing**, and **topological sort** — they double as Round-3
machine-coding building blocks.

---

## Java specifics to have sharp

- **Collections:** `HashMap`, `LinkedHashMap` (access-order = free LRU!), `TreeMap`,
  `PriorityQueue`, `ArrayDeque`, `ConcurrentHashMap`.
- **Complexity of operations** on each; when a `TreeMap` (log n, ordered) beats a `HashMap`.
- **Concurrency:** `ConcurrentHashMap`, `AtomicInteger`/`LongAdder`, `ReentrantLock`,
  `ReadWriteLock`, `Semaphore` — you'll likely be asked to make a structure thread-safe.
- **Streams & `CompletableFuture`** for clean, parallel processing.
- **Virtual threads (Java 21)** — good to mention for high-concurrency I/O platforms.

> 💡 `LinkedHashMap(capacity, 0.75f, true)` with an overridden `removeEldestEntry` gives you an
> **LRU cache in ~5 lines** — know this cold; it's a frequent "impress me" answer.

---

## The "design" half

After DSA they often pivot: *"Now design the system this lives in."* Keep it lightweight (full
depth is Round 4). Example pivots:

- Solved LRU cache → *"Design a distributed cache"* (sharding, consistency, eviction, TTL,
  hot keys). See Round 4.
- Solved sliding-window counting → *"Design an API rate limiter"* (token bucket vs sliding
  window, per-tenant, Redis-backed, distributed). See Round 3 & 4.
- Solved Top-K frequent → *"Design API usage analytics / top endpoints"* (streaming, count-min
  sketch, approximate top-K).

**Framework for the mini-design:** clarify requirements & scale → API → data model → core
algorithm/data structure → scaling (partitioning, replication) → failure modes → trade-offs.

---

## Practice checklist

- [ ] Can implement **LRU** two ways (manual DLL+map, and `LinkedHashMap`) and **LFU**.
- [ ] Can implement a **sliding-window / token-bucket rate limiter** and analyze it.
- [ ] Comfortable with **heaps** (Top-K, merge-k) and **Trie** (insert/search/prefix).
- [ ] **Topological sort** (Kahn's + DFS) for dependency graphs.
- [ ] Can make any of the above **thread-safe** and explain the locking choice.
- [ ] State time/space complexity automatically for everything you write.
- [ ] Have done ~30–40 mixed problems on the patterns above (Blind-75 / NeetCode-150 subset).

---

**Next → [Round 3: Coding + Machine Coding](Round-3-Coding-and-Machine-Coding.md)**
