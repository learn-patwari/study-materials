[← Round 2](Round-2-DSA-and-Design.md) · [Role index](README.md) · [Next: Round 4 →](Round-4-Architecture-Design.md)

# Round 3 — Technical Coding + Machine Coding

> **Format:** Two things. **Technical coding** = write correct, clean code for a focused problem
> (often concurrency- or API-flavored). **Machine coding** = build a small but *complete, running,
> extensible* system in ~60–90 min — usually in-memory, no DB, but well-structured OOP with clean
> abstractions. They grade **design quality** (SOLID, extensibility), correctness, and code
> cleanliness far more than clever algorithms.

---

## What machine-coding interviewers actually score

| They want | What it looks like |
|-----------|--------------------|
| **Clean abstractions** | Interfaces for the varying parts (strategies), small classes, clear names |
| **SOLID / OCP** | New behavior = new class, not editing a giant `switch` |
| **Working code** | It compiles and runs; a `main`/tests demo the happy path + one edge |
| **Extensibility** | "Add feature X" is a 5-minute change, and you designed for it |
| **Concurrency awareness** | Thread-safety where it matters, explained |
| **Incremental delivery** | A working core first, then layer features — don't gold-plate early |

> ⚠️ **Time trap:** don't over-engineer up front. Get a **working vertical slice**, then extend.
> Announce your plan: "I'll model the core entities, get one flow working, then add strategies."

---

## Design patterns to have in your pocket

- **Strategy** — pluggable algorithms (rate-limit policy, eviction policy, routing rule, auth
  scheme). *Your #1 tool in these rounds.*
- **Factory** — create the right strategy/handler from config.
- **Builder** — construct complex request/response/config objects.
- **Observer / pub-sub** — event notifications.
- **Decorator / Chain of Responsibility** — middleware pipelines (auth → rate-limit → log →
  route). *Extremely relevant to an API gateway.*
- **Singleton (careful)** — a registry/config, ideally DI-managed.
- **Template method** — fixed skeleton, overridable steps.

---

## High-probability machine-coding problems for THIS role

The team is API-platform, so expect API/gateway/infra-flavored prompts:

1. **API Rate Limiter** — per-client limits, pluggable algorithm (token bucket / fixed / sliding
   window), thread-safe. *(Worked example below.)*
2. **In-memory cache with TTL + eviction** — LRU/LFU strategy, expiry, thread-safe.
3. **API Gateway request pipeline** — middleware chain (auth, rate-limit, logging, routing) using
   Chain of Responsibility.
4. **Pub/Sub system** — topics, subscribers, publish, at-least-once delivery, optional retention.
5. **API key / token management** — issue, validate, scope, expire keys.
6. **URL routing / path matcher** — trie-based route matching with path params (`/users/{id}`).
7. **Load balancer** — strategies (round-robin, least-connections, weighted).

Prepare by **actually building** 2–3 of these end-to-end in Java before the interview.

---

## Worked example: a clean, extensible Rate Limiter

Shows the abstractions they look for — a **Strategy** interface, per-key isolation, thread-safety.

```java
// --- Strategy: the varying part is the algorithm ---
public interface RateLimiterStrategy {
    boolean allowRequest(String clientId);
}

// --- Token bucket implementation ---
public class TokenBucketStrategy implements RateLimiterStrategy {
    private final long capacity;         // max tokens
    private final double refillPerSec;   // tokens added per second
    private final Map<String, Bucket> buckets = new ConcurrentHashMap<>();

    public TokenBucketStrategy(long capacity, double refillPerSec) {
        this.capacity = capacity;
        this.refillPerSec = refillPerSec;
    }

    @Override
    public boolean allowRequest(String clientId) {
        Bucket b = buckets.computeIfAbsent(clientId, k -> new Bucket(capacity));
        return b.tryConsume(capacity, refillPerSec);
    }

    // Per-client bucket; synchronized only on its own instance -> good concurrency
    private static class Bucket {
        private double tokens;
        private long lastRefillNanos;
        Bucket(double initial) {
            this.tokens = initial;
            this.lastRefillNanos = System.nanoTime();
        }
        synchronized boolean tryConsume(long capacity, double refillPerSec) {
            long now = System.nanoTime();
            double elapsedSec = (now - lastRefillNanos) / 1_000_000_000.0;
            tokens = Math.min(capacity, tokens + elapsedSec * refillPerSec);
            lastRefillNanos = now;
            if (tokens >= 1) { tokens -= 1; return true; }
            return false;
        }
    }
}

// --- The limiter delegates to whatever strategy is injected (OCP) ---
public class RateLimiter {
    private final RateLimiterStrategy strategy;
    public RateLimiter(RateLimiterStrategy strategy) { this.strategy = strategy; }
    public boolean allow(String clientId) { return strategy.allowRequest(clientId); }
}
```

**Why this scores well:** the algorithm is a swappable `Strategy` (add sliding-window without
touching `RateLimiter`), per-client `ConcurrentHashMap` isolates contention, locking is scoped to
a single bucket, and it's trivially unit-testable. **Talk through** the distributed version too:
move counters to **Redis** (atomic `INCR`+`EXPIRE`, or a Lua script for token bucket) so limits
hold across many gateway instances — ties straight to your Redis experience.

---

## Technical-coding (focused) prep

Expect a smaller, correctness-focused problem, often concurrency-flavored. Be fluent in:
- A **thread-safe bounded blocking queue** (wait/notify or `ReentrantLock`+`Condition`).
- A **producer/consumer** with `BlockingQueue`.
- Building an **LRU cache** (manual and `LinkedHashMap`).
- Parsing/normalizing input (e.g., parse a route/query string) with clean edge handling.
- Using `CompletableFuture` to fan-out/fan-in calls (relevant to API aggregation).

---

## Round-3 checklist

- [ ] Built **2–3 machine-coding systems** end-to-end in Java (rate limiter, TTL cache, pub/sub).
- [ ] Default to **Strategy + Factory + Chain-of-Responsibility**; can justify each.
- [ ] Deliver a **working core first**, then extend — narrate the plan.
- [ ] Thread-safety: know where to use `ConcurrentHashMap`, `synchronized`, `ReentrantLock`.
- [ ] Can describe the **distributed/Redis-backed** version of whatever you build in-memory.
- [ ] Write a tiny `main`/tests to demo it runs.

---

**Next → [Round 4: Architecture-level System Design](Round-4-Architecture-Design.md)**
