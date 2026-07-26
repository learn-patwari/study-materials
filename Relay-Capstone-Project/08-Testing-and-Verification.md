[← Tracing & Console](07-Tracing-and-Console.md) · [Relay README](README.md) · [Next: Implementation Roadmap →](09-Implementation-Roadmap.md)

# 8. Testing & Verification

Verification proves the guarantees are real. Two layers: **automated tests** for each guarantee,
and a **live kill-and-resume demo** that proves exactly-once in front of people.

## 8.1 What must be tested (the guarantees, one by one)

| Area | Test focus |
|------|-----------|
| **Publish validation** | Dangling `next`, missing `start`, unreachable nodes, malformed sensitive node → publish rejected with clear issues |
| **Template resolution** | `{{node.field}}` resolves from prior outputs; missing key → typed error, not silent blank |
| **Schema enforcement (AI)** | Valid output flows; invalid output fails (and bounded repair-retry works); only typed fields reach downstream |
| **Idempotency** | Re-executing a side-effecting node with the same key performs the effect once; second call replays stored result |
| **Guardrails** | Max-step cap fails runaway loops; sensitive node hard-blocks without approval; HMAC rejects forged webhooks |
| **Pause/resume** | Run parks at approval; grant resumes from the right node; reject fails cleanly |
| **Crash recovery** | Killing a worker mid-step resumes from last completed step with **zero duplicate side effects** |
| **Concurrency** | Many in-flight runs don't interfere; a run is advanced by one worker at a time |

## 8.2 Test types & tooling

- **Unit tests** (JUnit 5): template resolver, schema validator, condition evaluator, HMAC verify,
  idempotency wrapper, definition validator.
- **Integration tests** (Testcontainers Postgres): full run through the real engine + DB; outbox
  claim/`SKIP LOCKED`; approval pause/resume; retry/backoff.
- **Mocked externals**: HTTP and LLM adapters are deterministic fakes — a "flaky" mode injects
  failures/latency to exercise retries and crash paths.
- **Concurrency tests**: N workers + M runs; assert no double side effects (count `side_effects`
  rows) and no cursor races.

## 8.3 The kill-and-resume demo (the headline proof)

A scripted, repeatable demo that shows exactly-once holds under a real crash:

```
1. Publish a workflow whose middle node is a side-effecting http_request (mocked "place order").
2. Trigger a run; let it execute up to just before/inside that node.
3. HARD-KILL the worker process mid-step (kill -9).
4. Start a fresh worker.
5. Observe: the run resumes from the last completed step; the side effect fires exactly once
   (side_effects has a single row; the mock "world" recorded one order).
6. Show the trace: the redelivered attempt replayed the stored result instead of re-calling.
```

**Acceptance:** `SELECT count(*) FROM side_effects WHERE run_id=… AND node_id='place_order'` = **1**,
and the mocked external world shows exactly one order — proving **zero duplicate side effects**.

## 8.4 CI

- Run unit + integration tests on every push (Testcontainers spins Postgres).
- Lint + build; fail the build on any guarantee test regressing.
- Optionally publish the trace of the demo run as a build artifact.

---

**Next → [9. Implementation Roadmap](09-Implementation-Roadmap.md)**
