#!/usr/bin/env bash
#
# Phase-10 kill-and-resume demo.
#
# Proves two Relay guarantees in front of people:
#   1. Durability  — a run's state survives a HARD crash (kill -9) of the app, because all
#                    state lives in Postgres. A run parked at an approval gate is still parked
#                    after the process is killed and restarted.
#   2. Exactly-once — after resuming, the sensitive side effect fires exactly once
#                    (side_effects has a single row for the charge node).
#
# Requires: docker compose, curl, python3. Run from Relay-Capstone-Project/relay/.
set -euo pipefail
cd "$(dirname "$0")/.."

BASE=http://localhost:8080
say() { printf "\n\033[1;36m== %s ==\033[0m\n" "$*"; }
json_get() { python3 -c "import sys,json; print(json.load(sys.stdin)$1)"; }

say "1. Start Postgres + Relay (docker compose up --build)"
docker compose up -d --build

say "2. Wait for the app to be healthy"
for i in $(seq 1 60); do
  if curl -fsS "$BASE/actuator/health" >/dev/null 2>&1; then break; fi
  sleep 2
done

say "3. Create a workflow whose charge node is sensitive (hard-blocked without approval)"
WF=$(curl -fsS "$BASE/api/workflows" -H 'Content-Type: application/json' -d '{"name":"kill-demo"}')
WID=$(echo "$WF" | json_get "['id']")
echo "workflow id: $WID"

curl -fsS "$BASE/api/workflows/$WID/versions" -H 'Content-Type: application/json' -d '{
  "start":"charge",
  "nodes":{
    "charge":{"type":"http_request","sensitive":true,"next":"done",
              "config":{"method":"POST","url":"https://api.mock/orders"}},
    "done":{"type":"notify","next":null,"config":{"to":"ops","template":"charged"}}
  }}' >/dev/null
curl -fsS -XPOST "$BASE/api/workflows/$WID/versions/1/publish" >/dev/null

say "4. Trigger a run — it will park at the approval gate (no side effect yet)"
RUN=$(curl -fsS -XPOST "$BASE/api/triggers/$WID/manual" -H 'Content-Type: application/json' -d '{"amount":2499}')
RID=$(echo "$RUN" | json_get "['runId']")
sleep 3
STATUS=$(curl -fsS "$BASE/api/runs/$RID" | json_get "['status']")
echo "run $RID status: $STATUS   (expected WAITING_APPROVAL)"

say "5. HARD KILL the app (kill -9 the container) and restart it"
docker compose kill app
docker compose up -d app
for i in $(seq 1 60); do
  if curl -fsS "$BASE/actuator/health" >/dev/null 2>&1; then break; fi
  sleep 2
done

say "6. After the crash+restart, the run is STILL parked (state survived in Postgres)"
STATUS=$(curl -fsS "$BASE/api/runs/$RID" | json_get "['status']")
echo "run $RID status: $STATUS   (still WAITING_APPROVAL => durable)"

say "7. Approve the gate — the run resumes and the charge fires"
APID=$(curl -fsS "$BASE/api/approvals?status=PENDING" | json_get "[0]['id']")
curl -fsS -XPOST "$BASE/api/approvals/$APID/grant" -H 'Content-Type: application/json' -d '{"decidedBy":"demo"}' >/dev/null
for i in $(seq 1 30); do
  STATUS=$(curl -fsS "$BASE/api/runs/$RID" | json_get "['status']")
  [ "$STATUS" = "SUCCEEDED" ] && break
  sleep 1
done
echo "run $RID status: $STATUS"

say "8. Verify EXACTLY-ONCE: side_effects rows for the charge node"
COUNT=$(docker compose exec -T db psql -U relay -d relay -tAc \
  "select count(*) from side_effects where run_id='$RID' and node_id='charge'")
echo "side_effects(charge) = $COUNT   (expected 1)"

if [ "$STATUS" = "SUCCEEDED" ] && [ "$COUNT" = "1" ]; then
  printf "\n\033[1;32mPASS: durable across crash, side effect performed exactly once.\033[0m\n"
else
  printf "\n\033[1;31mFAIL: status=%s count=%s\033[0m\n" "$STATUS" "$COUNT"; exit 1
fi

echo
echo "Tear down with: docker compose down -v"
