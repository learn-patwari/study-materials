# Relay Demos

## Kill-and-resume (Phase 10)

`kill-and-resume.sh` is a scripted, repeatable proof of Relay's two headline guarantees:

1. **Durability across a hard crash** — a run parked at an approval gate stays parked after the
   app is `kill -9`'d and restarted, because all state lives in Postgres (not in the process).
2. **Exactly-once side effects** — after the run resumes, the sensitive "charge" fires **once**
   (`side_effects` has exactly one row for that node).

### Run it

```bash
# from Relay-Capstone-Project/relay/
chmod +x demo/kill-and-resume.sh
./demo/kill-and-resume.sh
```

Requirements: `docker compose`, `curl`, `python3`.

The script starts Postgres + Relay via `docker-compose.yml`, publishes a workflow whose charge
node is `sensitive: true`, triggers a run (which parks at the gate), **hard-kills and restarts**
the app, shows the run is still parked, then approves it and asserts the run reaches `SUCCEEDED`
with `side_effects(charge) = 1`. Prints **PASS/FAIL**.

Tear down: `docker compose down -v`.

### Why the approval gate makes this deterministic

The gate gives a stable pause point to crash at — no timing races. It exercises the same
persistence and resume machinery that a mid-node crash relies on. The **mid-node** crash path
(worker dies while executing a side-effecting node) is covered deterministically by the automated
integration tests:

- `RelayEngineIT` — a redelivered node replays the ledgered result (no duplicate effect).
- `RetryIT` — a transient failure (flaky mock) before the effect is retried; the run still
  succeeds exactly-once.
