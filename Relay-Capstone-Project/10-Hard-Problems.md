[← Implementation Roadmap](09-Implementation-Roadmap.md) · [Relay README](README.md)

# 10. Where This Actually Gets Hard

Three things keep us honest. Naming them — and having a concrete answer for each — is what
separates a real design from a diagram.

## 10.1 Exactly-once side effects when workers crash mid-step

**The problem.** A worker calls the mocked external world ("place order"), then crashes *before*
recording that it did. The queue redelivers; a second worker must not place the order again.

**The solution.**
- Every side-effecting call is guarded by the **idempotency ledger**: `INSERT ... ON CONFLICT DO
  NOTHING` on `side_effects(run_id, node_id, attempt_key)`. Only the worker that wins the insert
  performs the effect; it then stores the result. A redelivered attempt finds the row and
  **replays the stored result** instead of re-calling.
- The step result, ledger row, cursor advance, and trace all commit in **one transaction**, so
  "did the work" and "recorded the work" can never diverge.
- Combined with **single-writer-per-run** (`SKIP LOCKED` claim), this yields **at-least-once
  execution, exactly-once side effects**.

**The honest caveat.** True exactly-once requires the *external* system to honor the idempotency
key too. In the capstone the mocked world does. For a real provider, you push the key to their
idempotency mechanism where one exists, and where it doesn't you accept at-least-once at that
boundary and design the consumer to dedupe. The engine does everything on *its* side to make the
effect single.

## 10.2 Keeping pause/resume correct with many concurrent runs

**The problem.** Dozens of runs are in flight; some park at approval gates, some resume, some
retry. The state machine must never double-advance a run, resume it at the wrong node, or resume a
rejected one.

**The solution.**
- **Single writer per run:** the `outbox` claim with `FOR UPDATE SKIP LOCKED` guarantees only one
  worker holds a given run's message at a time; the per-step transaction guarantees only one cursor
  advance commits.
- **The cursor is the single source of truth** for "where are we," and it only moves inside the
  committing transaction — so a resume always reads the true position.
- **Resume is idempotent on the gate:** granting inserts the outbox row in the same transaction as
  the approval decision; the worker **re-checks** the gate before proceeding, so a duplicate grant
  or a late redelivery can't push a rejected/again-pending run forward.
- **No shared mutable state across runs** — each run's progress lives entirely in its own rows.

## 10.3 The engine/AI trust boundary (the most important one)

**The problem.** It's tempting to let the LLM decide "this looks safe, proceed" or to have the
prompt "remember" to wait for approval. That is exactly how these systems fail.

**The solution — a hard line, enforced in code:**
- **Approval gates and the step cap live in the engine**, checked structurally on every node. The
  AI is never asked to enforce them and *cannot* — it has no path to approve a gate, raise the cap,
  or call an external system.
- The AI node emits **schema-validated data only**; control flow (branching, gating) depends solely
  on validated fields, so injected instructions in model output or inputs can't change what the
  engine does.
- Stated as a rule: **the engine guarantees; the model advises.** Anything that must be *true*
  (not just *likely*) is enforced by the engine and covered by a test.

---

## Summary

| Hard problem | Core mechanism |
|--------------|----------------|
| Exactly-once under crashes | Idempotency ledger (unique key + `ON CONFLICT`) + atomic per-step commit + single-writer-per-run |
| Concurrent pause/resume | `SKIP LOCKED` single-writer, cursor-as-truth, gate re-check on resume, per-run isolation |
| Engine vs AI trust | Structural enforcement of gates/caps in engine; AI emits validated data, never authority |

These three, solved together, are what make Relay a *durable* orchestrator rather than a script
that usually works.

---

[← Back to Relay README](README.md)
