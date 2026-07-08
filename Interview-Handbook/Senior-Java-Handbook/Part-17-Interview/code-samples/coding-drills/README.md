# Code samples — Chapter 17.01: Staff/Principal Engineer Interview Playbook

Three classic whiteboard coding-interview problems, implemented at
production quality (not just "passes the happy path") and backed by tests
that specifically exercise the follow-up questions an interviewer would
actually ask. No Spring Boot — these are meant to be readable and
reproducible in a plain-JDK context, the same constraint a live coding
round imposes.

```bash
mvn -q compile   # compiles cleanly against Java 21
mvn -q test      # JUnit 5 tests, all passing, including two real concurrency tests
```

| Class | Interview prompt it answers | Key follow-up it's built to survive |
|---|---|---|
| `TokenBucketRateLimiter` | "Design a rate limiter" | Why lock-based, not lock-free CAS — refill + consume must be observed atomically together |
| `ImmutableMoney` | "Design an immutable value object" | Why `equals`/`hashCode` must be overridden together, and the `BigDecimal` scale-vs-value equality trap |
| `PoisonPillWorkQueue` | "Design a producer-consumer queue with graceful shutdown" | Why a boolean "stop" flag can't wake a consumer blocked in `take()` — the sentinel/poison-pill pattern |

`PoisonPillWorkQueueTest` includes real concurrency tests (a consumer
started before any work exists, blocked in `take()`; a producer blocked on
a full queue) — these exercise actual thread scheduling, not just
single-threaded logic.
