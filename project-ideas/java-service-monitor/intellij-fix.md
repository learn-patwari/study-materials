# IntelliJ IDEA — Fix Java Process Detachment & 503 Errors

## The Problem

When you stop a run in IntelliJ, the Java process keeps running in the background
and serves HTTP 503 errors. This is caused by two separate known bugs:

| Bug | ID | Symptom |
|---|---|---|
| Debug stop doesn't kill app JVM | IDEA-184918 | Process visible in `jps` after clicking Stop |
| Gradle bootRun orphans app JVM | IDEA-196623 | Two processes launched; stopping one leaves the other |

Both are **IntelliJ-specific**. The JVM itself is fine — IntelliJ just isn't killing it.

---

## Fix 1 — Kill Process Immediately on Stop (Most Important)

**Settings → Build, Execution, Deployment → Debugger**

Enable: ✅ **"Kill the debug process immediately when stopping"**

> Without this, clicking Stop only detaches the debugger.
> The JVM process keeps running — still bound to the port, still serving (or crashing).

---

## Fix 2 — Give IntelliJ Direct Process Control

**Settings → Build, Execution, Deployment → Build Tools → Gradle**

Change **"Build and run using"** from `Gradle` → **`IntelliJ IDEA`**

> When Gradle runs the app, IntelliJ manages the Gradle daemon — not the app JVM.
> Stopping the run only kills Gradle; your Spring Boot / Java app lives on.
> With IntelliJ IDEA selected, IntelliJ owns the process and can kill it on stop.

*Note: This only applies if you're using a Gradle project. Maven projects are not affected.*

---

## Fix 3 — Add VM Options to Force Exit on OOM

**Run/Debug Configurations → Edit Configurations → VM Options**

```
-Xms512m -Xmx1g -XX:MaxMetaspaceSize=384m
-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/tmp/heapdumps
-XX:+ExitOnOutOfMemoryError
-Xlog:gc*:file=/tmp/gc.log:time,uptime:filecount=3,filesize=10m
```

`-XX:+ExitOnOutOfMemoryError` ensures the JVM terminates cleanly on first OOM
instead of entering a zombie 503 state.

Full flag reference: see `jvm-flags.txt`.

---

## The 3 Separate JVM Heaps in IntelliJ (Common Confusion)

IntelliJ runs three independent JVMs. Each has its own heap:

| JVM | Memory Setting | Location |
|---|---|---|
| **IntelliJ IDE itself** | `-Xmx` in `idea.vmoptions` | Help → Edit Custom VM Options |
| **Build/compilation process** | "Shared build process heap" | Settings → Build → Compiler |
| **Your application** | `-Xmx` in VM Options | Edit Run Configuration → VM Options |

**Your 503 issue is in the third one — the application JVM.**
Increasing IDE or build heap does nothing to fix application memory pressure.

---

## Immediate Checklist

After any 503 / process detachment:

```bash
# 1. Check for orphaned Java processes
jps -l

# 2. Kill orphan by PID
kill -9 <PID>

# 3. Verify port is free before restarting
lsof -i :8080

# 4. Check for OOM in GC log
grep -i "outofmemory\|gc overhead" /tmp/gc.log

# 5. Check heap dump was written
ls -lh /tmp/heapdumps/*.hprof
```

---

## Analyzing a Heap Dump

```bash
# Quick analysis with jhat (JDK built-in)
jhat /tmp/heapdumps/heapdump-<PID>.hprof
# Open http://localhost:7000 in browser

# Better: Eclipse Memory Analyzer (MAT) — download from eclipse.org/mat
# Open the .hprof file → Run "Leak Suspects Report"
```

Look for:
- **Dominator tree**: which objects hold the most retained heap
- **Leak suspects**: MAT auto-detects the most likely culprits
- **OQL queries**: `SELECT * FROM java.lang.String s WHERE s.count > 10000` etc.
