# Java Service Monitor

A lightweight monitoring agent for any Java service — Spring Boot, Quarkus, Micronaut, plain Java, etc.

Detects HTTP 503 errors, heap pressure, GC overhead spikes, and orphaned JVM processes.
Also includes the root-cause fix for the IntelliJ IDEA process detachment bug that triggers this.

---

## Files

| File | Purpose |
|---|---|
| `monitor.sh` | Continuous monitoring loop — runs every 15s |
| `diagnose.sh` | On-demand snapshot — run immediately when 503 appears |
| `jvm-flags.txt` | JVM flags to paste into IntelliJ VM Options |
| `intellij-fix.md` | IntelliJ settings that fix process orphaning permanently |

---

## Quickstart

```bash
chmod +x monitor.sh diagnose.sh

# Basic usage (auto-detects first non-IDE Java process)
./monitor.sh

# Target a specific app by name (substring of main class or jar)
APP_NAME=MyApplication ./monitor.sh

# Custom port and thresholds
APP_NAME=MyApp PORT=9090 HEAP_WARN_PCT=75 HEAP_CRIT_PCT=85 ./monitor.sh

# On-demand snapshot when you see a 503
APP_NAME=MyApp ./diagnose.sh
```

---

## What It Monitors

| Check | Frequency | Action on Failure |
|---|---|---|
| Process presence (`jps`) | Every cycle | ALERT if missing for 3+ cycles |
| HTTP health (`/actuator/health`) | Every cycle | ALERT on 503 or connection refused |
| Old gen heap % (`jstat`) | Every cycle | WARN at 80%, auto heap dump at 90% |
| GC overhead % | Every cycle | WARN at 50%, ALERT + thread dump at 80% |

---

## Configuration

All settings are environment variables with sensible defaults:

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | _(auto)_ | Substring of main class or jar name |
| `PORT` | `8080` | HTTP port to health-check |
| `HEALTH_PATH` | `/actuator/health` | Health endpoint path |
| `CHECK_INTERVAL` | `15` | Seconds between checks |
| `HEAP_WARN_PCT` | `80` | Old gen % to log a warning |
| `HEAP_CRIT_PCT` | `90` | Old gen % to trigger automatic heap dump |
| `GC_OVERHEAD_PCT` | `80` | GC time % to trigger thread dump |
| `LOG_FILE` | `/tmp/java-monitor.log` | Log output path |
| `DUMP_DIR` | `/tmp/heapdumps` | Directory for heap dumps |

---

## Root Cause: Why Your Java Service Serves 503 from IntelliJ

### Scenario 1 — OOM Zombie (Most Common)

1. Service receives traffic, heap fills up
2. `OutOfMemoryError` kills a Tomcat worker thread
3. JVM process stays alive (OS still sees it running)
4. Tomcat thread pool drains → new requests get HTTP 503
5. IntelliJ shows "Running" — nothing looks wrong in the IDE

**Fix**: Add `-XX:+ExitOnOutOfMemoryError` to VM Options. This forces the JVM to exit on
first OOM instead of limping along in zombie state. See `jvm-flags.txt`.

### Scenario 2 — IntelliJ Process Detachment Bug

1. You click Stop in IntelliJ
2. IntelliJ detaches the debugger but does NOT kill the JVM (known bug IDEA-184918)
3. The old JVM keeps running, port still bound
4. You restart the service → port conflict → new instance fails → 503

**Fix**: Two IntelliJ settings toggles. See `intellij-fix.md`.

### Scenario 3 — GC Overhead Exhaustion

1. Heap is 95%+ full; GC runs constantly (> 98% of CPU time)
2. Application threads get no CPU → Tomcat request queue fills up
3. New requests rejected with HTTP 503 while GC churns

**Fix**: Increase `-Xmx`, enable GC logging, identify memory leak via heap dump.

---

## Analyzing Output

### Heap dump (`.hprof`)
```bash
# Quick: built-in JDK tool
jhat /tmp/heapdumps/heapdump-<PID>.hprof
# → open http://localhost:7000

# Better: Eclipse Memory Analyzer (MAT)
# Download from eclipse.org/mat → open .hprof → "Leak Suspects Report"
```

### GC log (`/tmp/gc.log`)
```bash
# Look for OOM and long GC pauses
grep -i "pause\|outofmemory\|overhead" /tmp/gc.log | tail -30

# GC log analyzer tools: GCViewer, GCEasy (web)
```

### Thread dump (`.txt`)
```bash
# Count threads by state
grep "java.lang.Thread.State:" /tmp/threaddump-*.txt | sort | uniq -c | sort -rn

# Find BLOCKED threads (waiting for a lock — potential deadlock)
grep -A5 "BLOCKED" /tmp/threaddump-*.txt
```

### JFR recording (`.jfr`)
```bash
# Open in JDK Mission Control (JMC)
# Download from adoptium.net → open .jfr file
# Key views: Memory tab, GC tab, Threads tab, Hot Methods
```

---

## Requirements

- JDK 11+ (uses `jcmd`, `jstat`, `jps`)
- `curl` (for HTTP health check)
- `bash` (macOS or Linux)
- Optional: Spring Boot Actuator (`/actuator/health` endpoint)

No external libraries or agents required.
