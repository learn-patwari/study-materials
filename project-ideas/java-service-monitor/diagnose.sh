#!/bin/bash
# ─────────────────────────────────────────────────────────────────
#  Java Service Diagnostics — on-demand snapshot
#  Run this the moment you see a 503 or suspect memory issues.
# ─────────────────────────────────────────────────────────────────

APP_NAME="${APP_NAME:-}"
PORT="${PORT:-8080}"
DUMP_DIR="${DUMP_DIR:-/tmp/heapdumps}"

RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

section() { echo -e "\n${BOLD}${CYAN}══ $* ══${RESET}"; }
mkdir -p "$DUMP_DIR"

# ── 1. Find process ───────────────────────────────────────────────
section "Running Java Processes"
jps -lv 2>/dev/null
echo ""

if [ -n "$APP_NAME" ]; then
  PID=$(jps -l 2>/dev/null | grep -i "$APP_NAME" | awk '{print $1}' | head -1)
else
  PID=$(jps -l 2>/dev/null | grep -v -E '^[0-9]+ (Jps|sun\.|com\.intellij)' | awk '{print $1}' | head -1)
fi

if [ -z "$PID" ]; then
  echo -e "${RED}[ERROR] No Java process found. Service may be fully down.${RESET}"
  echo "Check for orphaned processes: ps aux | grep java"
  ps aux | grep java | grep -v grep
  exit 1
fi

echo -e "${GREEN}Target PID: $PID${RESET}"

# ── 2. HTTP check ─────────────────────────────────────────────────
section "HTTP Health Check (:$PORT)"
curl -v --max-time 5 "http://localhost:${PORT}/actuator/health" 2>&1 || \
  echo -e "${YELLOW}Health endpoint unreachable — trying root path${RESET}"
curl -s -o /dev/null -w "HTTP %{http_code} from /\n" --max-time 5 "http://localhost:${PORT}/" 2>/dev/null

# ── 3. GC stats ───────────────────────────────────────────────────
section "GC Statistics (jstat -gcutil, 5 samples)"
jstat -gcutil "$PID" 1000 5 2>/dev/null
echo ""
echo "Columns: S0% S1% Eden% Old% Metaspace% YGC YGCT FGC FGCT GCT(total)"

# ── 4. Heap info ──────────────────────────────────────────────────
section "Heap Info (jcmd GC.heap_info)"
jcmd "$PID" GC.heap_info 2>/dev/null

# ── 5. Thread dump ────────────────────────────────────────────────
section "Thread Dump (jcmd Thread.print)"
THREAD_DUMP_FILE="/tmp/threaddump-${PID}-$(date +%Y%m%d-%H%M%S).txt"
jcmd "$PID" Thread.print 2>/dev/null | tee "$THREAD_DUMP_FILE"
echo -e "\n${GREEN}Thread dump saved → $THREAD_DUMP_FILE${RESET}"

# ── 6. Thread states summary ──────────────────────────────────────
section "Thread State Summary"
if [ -f "$THREAD_DUMP_FILE" ]; then
  echo "BLOCKED  : $(grep -c 'java.lang.Thread.State: BLOCKED'  "$THREAD_DUMP_FILE" 2>/dev/null || echo 0)"
  echo "WAITING  : $(grep -c 'java.lang.Thread.State: WAITING'  "$THREAD_DUMP_FILE" 2>/dev/null || echo 0)"
  echo "TIMED_W  : $(grep -c 'java.lang.Thread.State: TIMED_W'  "$THREAD_DUMP_FILE" 2>/dev/null || echo 0)"
  echo "RUNNABLE : $(grep -c 'java.lang.Thread.State: RUNNABLE' "$THREAD_DUMP_FILE" 2>/dev/null || echo 0)"
fi

# ── 7. VM flags ───────────────────────────────────────────────────
section "Active JVM Flags"
jcmd "$PID" VM.flags 2>/dev/null

# ── 8. Heap dump (optional) ───────────────────────────────────────
section "Heap Dump (Optional)"
read -r -p "Trigger heap dump now? This pauses the JVM briefly. [y/N] " answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
  DUMP_FILE="${DUMP_DIR}/heapdump-${PID}-$(date +%Y%m%d-%H%M%S).hprof"
  echo "Writing heap dump to $DUMP_FILE ..."
  jcmd "$PID" GC.heap_dump "$DUMP_FILE" && \
    echo -e "${GREEN}Done. Analyze with: jhat $DUMP_FILE OR Eclipse MAT${RESET}" || \
    echo -e "${RED}Heap dump failed — process may have exited${RESET}"
else
  echo "Skipped. To dump later: jcmd $PID GC.heap_dump $DUMP_DIR/heap.hprof"
fi

# ── 9. JFR snapshot ───────────────────────────────────────────────
section "JFR Recording (Optional)"
read -r -p "Start a 30-second JFR recording? [y/N] " answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
  JFR_FILE="/tmp/recording-${PID}-$(date +%Y%m%d-%H%M%S).jfr"
  jcmd "$PID" JFR.start duration=30s filename="$JFR_FILE" name=diag 2>/dev/null && \
    echo -e "${GREEN}Recording started. File → $JFR_FILE (auto-saves after 30s)${RESET}" || \
    echo -e "${YELLOW}JFR not available — add -XX:+FlightRecorder to VM options${RESET}"
else
  echo "Skipped. Manual: jcmd $PID JFR.start duration=60s filename=/tmp/app.jfr"
fi

echo -e "\n${BOLD}${GREEN}Diagnostics complete.${RESET}"
echo "Files saved:"
[ -f "$THREAD_DUMP_FILE" ] && echo "  Thread dump → $THREAD_DUMP_FILE"
ls "$DUMP_DIR"/*.hprof 2>/dev/null | xargs -I{} echo "  Heap dump  → {}"
