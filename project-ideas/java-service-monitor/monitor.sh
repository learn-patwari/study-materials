#!/bin/bash
# ─────────────────────────────────────────────────────────────────
#  Java Service Monitor — detects 503s, memory pressure, and
#  orphaned JVM processes. Works with any Java framework.
# ─────────────────────────────────────────────────────────────────

# ── Config (override via env vars) ───────────────────────────────
APP_NAME="${APP_NAME:-}"                   # substring of main class or jar name
PORT="${PORT:-8080}"
HEALTH_PATH="${HEALTH_PATH:-/actuator/health}"
CHECK_INTERVAL="${CHECK_INTERVAL:-15}"     # seconds between checks
HEAP_WARN_PCT="${HEAP_WARN_PCT:-80}"       # Old gen % threshold for WARN
HEAP_CRIT_PCT="${HEAP_CRIT_PCT:-90}"       # Old gen % threshold for auto heap dump
GC_OVERHEAD_PCT="${GC_OVERHEAD_PCT:-80}"   # GC time % threshold for WARN
LOG_FILE="${LOG_FILE:-/tmp/java-monitor.log}"
DUMP_DIR="${DUMP_DIR:-/tmp/heapdumps}"

# ── Colors ───────────────────────────────────────────────────────
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

# ── Helpers ──────────────────────────────────────────────────────
ts()    { date '+%Y-%m-%d %H:%M:%S'; }
log()   { echo -e "$(ts) $*" | tee -a "$LOG_FILE"; }
ok()    { log "${GREEN}[OK]${RESET}    $*"; }
warn()  { log "${YELLOW}[WARN]${RESET}  $*"; }
alert() { log "${RED}[ALERT]${RESET} $*"; }
info()  { log "${CYAN}[INFO]${RESET}  $*"; }

mkdir -p "$DUMP_DIR"

find_pid() {
  if [ -n "$APP_NAME" ]; then
    jps -l 2>/dev/null | grep -i "$APP_NAME" | awk '{print $1}' | head -1
  else
    # fallback: first non-jps Java process
    jps -l 2>/dev/null | grep -v -E '^[0-9]+ (Jps|sun\.|com\.intellij)' | awk '{print $1}' | head -1
  fi
}

check_process() {
  local pid
  pid=$(find_pid)
  if [ -z "$pid" ]; then
    alert "No Java process found${APP_NAME:+ matching '$APP_NAME'} — service may have crashed or been orphaned."
    return 1
  fi
  echo "$pid"
}

check_http() {
  local pid=$1
  local url="http://localhost:${PORT}${HEALTH_PATH}"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null)

  case "$code" in
    200|204) ok  "HTTP $code — service healthy (PID $pid)" ;;
    503)     alert "HTTP 503 — service UP but unhealthy (PID $pid). OOM or thread pool exhaustion likely." ;;
    000)     alert "HTTP 000 — connection refused on :$PORT (PID $pid). Service may be stuck in GC or dead." ;;
    *)       warn "HTTP $code from :$PORT (PID $pid)" ;;
  esac
  echo "$code"
}

check_heap() {
  local pid=$1
  # jstat -gcutil columns: S0 S1 E O M CCS YGC YGCT FGC FGCT CGC CGCT GCT
  local stats
  stats=$(jstat -gcutil "$pid" 1000 1 2>/dev/null | tail -1)
  if [ -z "$stats" ]; then
    warn "jstat unavailable for PID $pid (process may have exited)"
    return
  fi

  local old_pct gc_total cpu_total gc_ratio
  old_pct=$(echo "$stats" | awk '{printf "%.0f", $4}')
  gc_total=$(echo "$stats" | awk '{print $NF}')          # GCT = total GC seconds
  cpu_total=$(ps -p "$pid" -o etimes= 2>/dev/null | tr -d ' ')

  if [ -n "$cpu_total" ] && [ "$cpu_total" -gt 0 ]; then
    gc_ratio=$(awk "BEGIN{printf \"%.0f\", ($gc_total / $cpu_total) * 100}")
  else
    gc_ratio=0
  fi

  # Heap report
  if [ "$old_pct" -ge "$HEAP_CRIT_PCT" ]; then
    alert "Old gen at ${old_pct}% (>= ${HEAP_CRIT_PCT}%) for PID $pid — triggering heap dump"
    trigger_heap_dump "$pid"
  elif [ "$old_pct" -ge "$HEAP_WARN_PCT" ]; then
    warn "Old gen at ${old_pct}% (>= ${HEAP_WARN_PCT}%) for PID $pid"
  else
    ok  "Old gen at ${old_pct}% for PID $pid"
  fi

  # GC overhead report
  if [ "$gc_ratio" -ge "$GC_OVERHEAD_PCT" ]; then
    alert "GC consuming ${gc_ratio}% of process uptime for PID $pid — GC overhead limit risk"
    print_thread_dump "$pid"
  elif [ "$gc_ratio" -ge 50 ]; then
    warn "GC at ${gc_ratio}% of uptime for PID $pid"
  fi
}

trigger_heap_dump() {
  local pid=$1
  local dump_file="${DUMP_DIR}/heapdump-${pid}-$(date +%Y%m%d-%H%M%S).hprof"
  info "Writing heap dump to $dump_file ..."
  jcmd "$pid" GC.heap_dump "$dump_file" 2>/dev/null && \
    info "Heap dump written: $dump_file" || \
    warn "Heap dump failed — process may have exited"
}

print_thread_dump() {
  local pid=$1
  info "Thread dump for PID $pid:"
  jcmd "$pid" Thread.print 2>/dev/null | tee -a "$LOG_FILE" | head -80
  info "(Full thread dump in $LOG_FILE)"
}

print_heap_info() {
  local pid=$1
  info "Heap info for PID $pid:"
  jcmd "$pid" GC.heap_info 2>/dev/null | tee -a "$LOG_FILE"
}

# ── Main loop ────────────────────────────────────────────────────
echo -e "${BOLD}"
echo "╔══════════════════════════════════════════╗"
echo "║     Java Service Monitor                 ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${RESET}"
info "Monitoring port=$PORT path=$HEALTH_PATH interval=${CHECK_INTERVAL}s heap_warn=${HEAP_WARN_PCT}% heap_dump=${HEAP_CRIT_PCT}%"
info "Logs → $LOG_FILE | Dumps → $DUMP_DIR"
echo ""

FAIL_COUNT=0

while true; do
  echo -e "${CYAN}── $(ts) ──────────────────────────────────────────────────${RESET}"

  pid=$(check_process)
  if [ -z "$pid" ]; then
    FAIL_COUNT=$((FAIL_COUNT + 1))
    [ "$FAIL_COUNT" -ge 3 ] && alert "Process missing for $((FAIL_COUNT * CHECK_INTERVAL))s — likely crashed"
  else
    FAIL_COUNT=0
    http_code=$(check_http "$pid")
    check_heap "$pid"

    # If 503 and heap is high, print combined diagnostic
    if [ "$http_code" = "503" ]; then
      print_heap_info "$pid"
    fi
  fi

  sleep "$CHECK_INTERVAL"
done
