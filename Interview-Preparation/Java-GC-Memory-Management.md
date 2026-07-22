# Java Garbage Collection & Memory Management — Experienced Interview Questions (Java 8–25)

> Target: Staff / Senior Engineer interviews. Covers fundamentals, algorithm internals, version-by-version evolution, tuning, diagnostics, and real-world war stories.

---

## Table of Contents

1. [JVM Memory Architecture](#1-jvm-memory-architecture)
2. [GC Fundamentals & Algorithms](#2-gc-fundamentals--algorithms)
3. [GC Evolution: Java 8 → 25](#3-gc-evolution-java-8--25)
4. [G1GC Deep Dive](#4-g1gc-deep-dive)
5. [ZGC Deep Dive](#5-zgc-deep-dive)
6. [Shenandoah GC](#6-shenandoah-gc)
7. [GC Tuning & JVM Flags](#7-gc-tuning--jvm-flags)
8. [Memory Leaks & Object Retention](#8-memory-leaks--object-retention)
9. [Metaspace, Off-Heap & Direct Memory](#9-metaspace-off-heap--direct-memory)
10. [Project Loom & Virtual Threads Impact](#10-project-loom--virtual-threads-impact)
11. [Observability: Logs, JFR, JMX](#11-observability-logs-jfr-jmx)
12. [Scenario-Based / Design Questions](#12-scenario-based--design-questions)

---

## 1. JVM Memory Architecture

### Q1. Draw and explain all JVM memory regions. Which are GC-managed and which are not?

**Answer:**

```
┌──────────────────────────────────────────────────────────────────┐
│                          JVM Process Memory                      │
│                                                                  │
│  ┌─────────────────────── Heap (GC-managed) ─────────────────┐  │
│  │  Young Gen              Old Gen (Tenured)                  │  │
│  │ ┌───────┬────┬────┐    ┌────────────────────────────────┐  │  │
│  │ │ Eden  │ S0 │ S1 │    │         Old / Tenured          │  │  │
│  │ └───────┴────┴────┘    └────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────── Non-Heap (partially GC-managed) ──────────────┐  │
│  │  Metaspace (class metadata) | Code Cache (JIT compiled)   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────── Off-Heap (NOT GC-managed) ──────────────────┐  │
│  │  Direct ByteBuffers | Memory-Mapped Files | Thread Stacks  │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

| Region | GC Managed | Notes |
|--------|-----------|-------|
| Eden | Yes | New allocations land here |
| Survivor (S0/S1) | Yes | Objects that survive Minor GC |
| Old/Tenured | Yes | Long-lived objects |
| Metaspace | Partially | Class metadata; collected on full GC |
| Code Cache | No | JIT compiled native code |
| Thread Stacks | No | Stack frames per thread |
| Direct Memory | No | `ByteBuffer.allocateDirect()` |

**Key follow-up:** Thread stacks are per-thread; with virtual threads (Java 21+), stack chunks can be heap-allocated, blurring the boundary.

---

### Q2. What happened to PermGen in Java 8? What problems did it solve?

**Answer:**

**Before Java 8 (PermGen):**
- Fixed-size region inside the JVM heap for class metadata, interned strings, static variables
- Common cause of `java.lang.OutOfMemoryError: PermGen space` in app servers
- Size had to be tuned upfront with `-XX:MaxPermSize`
- GC of PermGen only triggered on Full GC — infrequent and expensive

**Java 8 change — Metaspace:**
- Metaspace moved class metadata to **native memory** (outside heap)
- Interned strings moved to the **heap** (Old Gen)
- Static variables references moved to the **heap**
- Metaspace grows dynamically, bounded only by available native memory
- `-XX:MaxMetaspaceSize` sets a cap (no cap by default)

**Problems solved:**
1. No more `PermGen OutOfMemoryError` from fixed sizing
2. Better GC — class unloading more efficient
3. Simpler tuning model

**New risk introduced:** Unbounded Metaspace growth can exhaust native memory. Always set `-XX:MaxMetaspaceSize` in production.

---

### Q3. Explain the difference between stack memory and heap memory for object lifetimes.

**Answer:**

| Aspect | Stack | Heap |
|--------|-------|------|
| Scope | Thread-local | Shared across threads |
| Lifetime | Tied to method frame | Until GC collects it |
| Allocation speed | O(1) — pointer bump | Slower (TLAB allocation) |
| Size | Small (default 512KB–1MB per thread) | Configured with `-Xmx` |
| Escape Analysis | JVM may allocate on stack if object doesn't escape | Yes, via `-XX:+DoEscapeAnalysis` |

**Escape Analysis (Java 6+, mature in Java 8+):**
- JIT compiler detects objects that don't escape the method
- Such objects can be **stack-allocated** or **scalar replaced** (fields stored in CPU registers)
- Zero GC pressure for those objects
- `-XX:+EliminateAllocations` enables scalar replacement

```java
// JVM may scalar-replace Point — never allocates on heap
public double distance(double x1, double y1, double x2, double y2) {
    Point p = new Point(x1 - x2, y1 - y2); // may be stack-allocated
    return Math.sqrt(p.x * p.x + p.y * p.y);
}
```

---

## 2. GC Fundamentals & Algorithms

### Q4. Explain the generational hypothesis. Why do most JVMs use generational GC?

**Answer:**

The **weak generational hypothesis** observes that:
> Most objects die young.

Evidence: In typical Java apps, 80–98% of objects are unreachable within milliseconds of allocation (short-lived iterator objects, temporary buffers, request-scoped data).

**Why generations help:**

1. **Cheaper Minor GC:** Only scan young gen (~5–10% of heap). Collection takes 1–50ms vs hundreds of ms for full heap.
2. **High allocation throughput:** New objects allocated via pointer-bump in Eden — extremely fast (near-zero cost).
3. **Old gen collected infrequently:** Long-lived objects are promoted once and rarely collected.

**Cost of crossing generations:** The **card table** (a 512-byte granularity dirty-bit array) tracks old→young references so Minor GC doesn't have to scan the entire old gen. Writing to an old-gen object marks its card dirty (write barrier).

**Generational ZGC (Java 21+)** brings this benefit to ZGC, which was previously non-generational.

---

### Q5. Compare Mark-Sweep, Mark-Compact, and Copying GC algorithms. When does each shine?

**Answer:**

**Mark-Sweep:**
```
Before: [A][_][B][_][_][C][_]
After:  [A][_][B][_][_][C][_]  (freed gaps remain)
```
- Pros: No object movement, fast collection
- Cons: Heap fragmentation; allocation requires free-list search
- Used by: CMS Old Gen

**Mark-Compact:**
```
Before: [A][_][B][_][_][C][_]
After:  [A][B][C][___________]
```
- Pros: No fragmentation, pointer-bump allocation restored
- Cons: Object movement requires updating all references (expensive)
- Used by: Serial/Parallel GC Old Gen, G1 mixed GC

**Copying (Semi-Space):**
```
From-space: [A][B][C]
To-space:   (empty)
After copy: From=(empty), To=[A][B][C]
```
- Pros: Only live objects traversed; allocation is pointer-bump; inherently compacting
- Cons: 50% space overhead; not suitable for large heaps
- Used by: Young Gen in all generational collectors (Eden → Survivor)

**In practice:** Modern collectors combine these — Copying for Young Gen, Mark-Compact or Mark-Sweep for Old Gen.

---

### Q6. What is a Stop-The-World (STW) pause? What GC work can be done concurrently?

**Answer:**

**STW:** All application threads are suspended while the GC performs a phase. Needed when GC must see a consistent snapshot of the heap.

**Phases that are typically STW:**
- Initial Mark (root scanning) — very short
- Remark / Final Mark — catch changes since initial scan
- Evacuation / Compaction (in some collectors)

**Concurrent phases (app threads run alongside GC threads):**
- Concurrent Mark (G1, ZGC, Shenandoah, CMS)
- Concurrent Reference Processing
- Concurrent Cleanup/Sweep
- ZGC: Concurrent Relocation (unique — even object moves are concurrent)
- Shenandoah: Concurrent Evacuation

**Write Barriers** enable concurrency: When an app thread modifies a reference during concurrent marking, a write barrier records the change so GC doesn't miss it (SATB — Snapshot At The Beginning in G1/ZGC).

**Read Barriers** (ZGC, Shenandoah): App threads check a "load barrier" on every object reference load to detect if the object has been moved and redirect to the new location.

---

### Q7. What is a write barrier and a read barrier? Which GCs use which?

**Answer:**

**Write Barrier:** Code injected by JIT before every object field write. Used to maintain GC invariants.

Uses:
- **Card table marking** (generational GCs): Mark card dirty when old→young reference written
- **SATB (Snapshot At The Beginning):** G1, ZGC — records the pre-write value so concurrent marking doesn't miss objects that get unreferenced after mark starts
- **Incremental Update:** CMS — records post-write value (can miss some, needs a remark phase)

**Read Barrier:** Code injected before every object reference load. More expensive than write barriers.

Uses:
- **ZGC Load Barrier:** Checks if reference points to a relocated object; if so, heals the reference to the new location. This is how ZGC achieves concurrent relocation without STW.
- **Shenandoah:** Brooks pointer indirection — each object has a forwarding pointer field checked on every read.

**Performance cost:** Read barriers are on the critical path of every field access (~1–5% throughput overhead). ZGC's colored pointers reduce this cost by encoding GC state in the unused high bits of a 64-bit pointer.

---

## 3. GC Evolution: Java 8 → 25

### Q8. Walk me through the default GC changes from Java 8 to Java 25.

**Answer:**

| Java Version | Default GC | Key Changes |
|---|---|---|
| Java 8 | Parallel GC | PermGen → Metaspace. G1 available but not default. CMS deprecated track begins. |
| Java 9 | G1GC | G1 becomes default. String deduplication in G1. Compact Strings (Latin-1 optimization). |
| Java 10 | G1GC | Parallel Full GC for G1 (was single-threaded before). JVMCI (GraalVM JIT) API. |
| Java 11 | G1GC | Epsilon GC (no-op). ZGC experimental (Linux x64 only). Low-overhead heap profiling. |
| Java 12 | G1GC | Shenandoah experimental (JEP 189). G1 Abortable Mixed Collections. G1 Promptly Return Unused Memory. |
| Java 13 | G1GC | ZGC: Uncommit unused memory. |
| Java 14 | G1GC | ZGC on Windows & macOS. CMS **removed** (JEP 363). Serial GC on low-core/low-memory machines. |
| Java 15 | G1GC | ZGC & Shenandoah **production-ready** (out of experimental). |
| Java 16 | G1GC | ZGC concurrent thread-stack processing (reduce STW). |
| Java 17 | G1GC | G1 Region Size adaptive improvements. Sealed classes (compile-time, not GC related). |
| Java 21 | G1GC | **Generational ZGC** (JEP 439, experimental). Virtual Threads GA. |
| Java 22 | G1GC | Generational ZGC improvements. |
| Java 23 | G1GC | Generational ZGC default mode. |
| Java 25 (LTS) | G1GC | Generational ZGC mature. ZGC main mode. Project Loom full GA. |

**Key milestones to remember:**
- **Java 8:** PermGen dies, Metaspace born
- **Java 9:** G1 becomes default
- **Java 11:** ZGC born (experimental)
- **Java 14:** CMS killed
- **Java 15:** ZGC & Shenandoah production-ready
- **Java 21:** Generational ZGC + Virtual Threads
- **Java 25:** Generational ZGC fully mature

---

### Q9. Why was CMS (Concurrent Mark Sweep) removed in Java 14? What replaced it?

**Answer:**

**CMS problems:**

1. **Concurrent Mode Failure:** If old gen fills up faster than CMS can collect, it falls back to a single-threaded Full GC — worst-case scenario, long STW pause.
2. **Heap Fragmentation:** CMS uses mark-sweep (no compaction). Over time, free space becomes fragmented. Promotion failures trigger Full GC.
3. **Incremental Update write barrier:** Can miss floating garbage, requiring a "remark" STW phase after concurrent mark.
4. **Complex tuning:** Many flags (`-XX:CMSInitiatingOccupancyFraction`, `-XX:+UseCMSInitiatingOccupancyOnly`, etc.) needed careful tuning.
5. **Maintenance burden:** Significant code complexity; G1 was already superior.

**Replacement path:**
- **G1GC** — low-pause, region-based, compacting; addresses fragmentation that plagued CMS
- **ZGC** — sub-millisecond pauses for applications where even G1's pauses are too high
- **Shenandoah** — similar to ZGC; concurrent evacuation

**Migration from CMS:**
```bash
# Before (Java 13 and earlier)
-XX:+UseConcMarkSweepGC -XX:CMSInitiatingOccupancyFraction=75

# After (Java 14+)
-XX:+UseG1GC  # or -XX:+UseZGC
```

---

### Q10. What is Epsilon GC and when would you use it?

**Answer:**

**Epsilon GC** (JEP 318, Java 11) is a no-op garbage collector — it allocates memory but **never reclaims it**. When the heap is exhausted, the JVM exits with an OOM error.

**Use cases:**

1. **Performance testing and benchmarking:** Eliminate GC pause variability from benchmark results. Measure true allocation throughput.
   ```bash
   java -XX:+UnlockExperimentalVMOptions -XX:+UseEpsilonGC -Xms8g -Xmx8g MyBenchmark
   ```

2. **Short-lived jobs:** Batch jobs that complete before exhausting the heap — no GC overhead at all.

3. **Memory footprint testing:** Measure exactly how much memory an app allocates before OOM.

4. **GC overhead measurement:** Run with Epsilon, then with G1 — the difference is GC overhead.

5. **JVM/library testing:** Libraries that need predictable, pause-free execution for verification.

**Not for:** Any long-running service with significant allocation.

---

### Q11. What did Compact Strings (Java 9, JEP 254) change about memory management?

**Answer:**

**Before Java 9:** All `String` objects stored characters as `char[]` (UTF-16, 2 bytes per character). ASCII strings ("hello", URLs, class names) wasted 1 byte per character.

**Java 9 change:** Strings now use `byte[]` with a coder field:
- `LATIN1` (coder=0): 1 byte per character for ASCII/Latin-1 strings
- `UTF16` (coder=1): 2 bytes per character for strings with non-Latin characters

**Memory impact:**
- Typical Java applications: **30–50% reduction in String memory usage**
- Reduces GC pressure significantly since Strings are the most common object type
- Interned strings, class names, method signatures — all benefit

**String Deduplication (G1, Java 8u20+):**
- Separate from Compact Strings
- G1 can scan young gen survivors for duplicate `String` objects with equal value
- Replaces their `char[]`/`byte[]` with a reference to a shared array
- Opt-in: `-XX:+UseStringDeduplication`
- Useful when many equal strings exist (e.g., repeated JSON keys, config values)

---

### Q12. Explain Generational ZGC introduced in Java 21. Why was non-generational ZGC not enough?

**Answer:**

**Original ZGC (Java 11–20): Non-Generational**
- Treated the entire heap as a single generation
- All objects — young and old — processed together in every GC cycle
- Problem: Short-lived objects mixed with long-lived objects; every cycle scans everything
- Higher CPU overhead; missed the benefit of the generational hypothesis

**Generational ZGC (JEP 439, Java 21 experimental; default Java 23+):**
- Splits heap into **Young Generation** and **Old Generation**
- Young gen collected frequently with cheap Minor GC cycles
- Old gen collected infrequently
- Retains ZGC's core properties: concurrent relocation, sub-millisecond STW pauses, colored pointers

**Benefits over non-generational ZGC:**
- **Lower CPU overhead** — most GC work on small young gen
- **Higher throughput** — less total work per application cycle
- **Better latency** — young gen cycles complete faster

**Enabling:**
```bash
# Java 21/22 (experimental)
-XX:+UseZGC -XX:+ZGenerational

# Java 23+ (default mode when using ZGC)
-XX:+UseZGC
```

**Non-generational ZGC** remains available with `-XX:-ZGenerational` for workloads with mostly long-lived objects where the generational split adds overhead without benefit.

---

## 4. G1GC Deep Dive

### Q13. Explain G1GC's region-based design. How does it differ from classic generational layout?

**Answer:**

**Classic Layout (Parallel/Serial GC):**
```
[<--- Young Gen --->][<---------- Old Gen ------------------>]
[Eden][S0][S1]       [          Contiguous Tenured           ]
```
Fixed contiguous areas. Resizing is expensive.

**G1GC Layout:**
```
[R][R][R][R][R][R][R][R][R][R][R][R][R][R][R][R]
 E  E  E  S  O  O  H  E  O  E  S  O  O  H  E  O
```
- Heap divided into equal-sized **regions** (1MB–32MB, power of 2)
- Each region is independently designated as Eden, Survivor, Old, or Humongous
- Regions are re-designated per GC cycle
- **Humongous regions:** Objects > 50% of region size allocated directly in old gen (one or more contiguous regions)

**Benefits:**
1. **Predictable pause targets:** `-XX:MaxGCPauseMillis=200` (soft goal)
2. **Incremental collection:** G1 collects the regions with most garbage first ("Garbage First")
3. **No fixed partition sizes:** Young/Old ratio adjusts dynamically
4. **Parallel and concurrent phases:** Both supported

**G1 Collection Cycle:**
1. **Young GC (Minor):** Evacuates Eden + Survivor regions → new Survivor regions
2. **Concurrent Mark Cycle:** Runs concurrent with application
   - Initial Mark (STW, piggybacked on Young GC)
   - Concurrent Root Region Scan
   - Concurrent Mark
   - Remark (STW)
   - Cleanup (STW for accounting, concurrent for freeing empty regions)
3. **Mixed GC:** Collects young + some old regions (post-marking)
4. **Full GC (fallback):** Single-threaded until Java 10, parallel from Java 10+

---

### Q14. What is G1's IHOP (Initiating Heap Occupancy Percent) and how does adaptive IHOP work?

**Answer:**

**IHOP** is the old gen occupancy threshold that triggers a concurrent marking cycle. If old gen fills before marking + mixed GC complete, G1 falls back to Full GC.

**Static IHOP (Java 8/9):**
```bash
-XX:InitiatingHeapOccupancyPercent=45  # default 45%
```
Fixed percentage; requires manual tuning based on application's promotion rate.

**Adaptive IHOP (Java 9+, default enabled):**
- G1 tracks the **allocation rate** into old gen and **marking duration** from previous cycles
- Predicts when the next marking cycle needs to start to finish before old gen fills
- Automatically adjusts IHOP — no manual tuning needed in most cases
- Disable with `-XX:-G1UseAdaptiveIHOP` for manual control

**Tuning when Adaptive IHOP isn't working:**
- Check GC logs for "to-space exhausted" or Full GC events
- If frequent: increase heap, reduce `-XX:MaxGCPauseMillis`, or tune `-XX:G1MixedGCCountTarget`
- If old gen utilization stays low: adaptive IHOP may be triggering too early; check allocation patterns

---

### Q15. What is a Humongous object in G1? Why can it cause problems?

**Answer:**

**Definition:** An object is "humongous" if its size exceeds 50% of a G1 region size.

**Allocation path:**
- Bypasses Eden; allocated directly in one or more contiguous Old Gen regions
- Size rounded up to the nearest region boundary (wasted space)
- Causes immediate old gen occupancy increase → may trigger early concurrent mark or even Full GC

**Problems:**

1. **Fragmentation:** Humongous regions must be contiguous; if heap is fragmented, allocation fails even with free space
2. **GC timing disruption:** Triggers marking cycle early; can destabilize G1's predictions
3. **Wasted space:** A 5MB object with 4MB regions wastes 3MB (allocated in 2 regions)
4. **Old gen pressure:** Increases IHOP triggering frequency

**Detection:**
```bash
# GC log shows:
[GC pause (G1 Humongous Allocation)]
```

**Solutions:**
- Increase region size: `-XX:G1HeapRegionSize=16m`
- Avoid large object allocations in hot paths (pool or reuse large byte arrays)
- Use `ByteBuffer.allocateDirect()` for large I/O buffers (off-heap, not managed by G1)
- Profile with JFR: `jdk.ObjectAllocationInNewTLAB` and `jdk.ObjectAllocationOutsideTLAB`

---

## 5. ZGC Deep Dive

### Q16. How does ZGC achieve sub-millisecond GC pauses while still doing relocation?

**Answer:**

ZGC's key innovation is **concurrent relocation** — objects are moved while application threads run. This requires solving the problem of stale references.

**Mechanism: Colored Pointers + Load Barrier**

**Colored Pointers:**
- On 64-bit systems, only 42–48 bits are used for addressing; ZGC uses remaining bits for GC metadata:
```
Bit layout of a ZGC reference (simplified):
[  unused  ][Finalizable][Remapped][Marked1][Marked0][ Object Address ]
    16 bits      1           1        1        1          44 bits
```

**Load Barrier:** Injected before every object reference load:
```java
// Conceptual (actual code is JIT-compiled native)
Object load(Object* ref) {
    Object obj = *ref;
    if (obj.colorBits != GOOD) {
        obj = slowPath(ref); // heal: get new address, update ref
    }
    return obj;
}
```

**Concurrent Relocation Phases:**
1. **Concurrent Mark:** Find live objects, mark colored pointers
2. **Concurrent Relocate:** Move objects to new locations, maintain forwarding table
3. **Concurrent Remap:** Update stale references — but this happens lazily via load barriers

**STW pauses in ZGC (sub-millisecond):**
- Initial Mark: Scan GC roots only (stack frames, registers) — proportional to thread count, not heap size
- Remark: Process remaining root updates
- Both pauses are O(thread count), not O(heap size)

**Result:** A 1TB heap can be collected with the same STW pause as a 1GB heap.

---

### Q17. How would you choose between G1 and ZGC for a production system?

**Answer:**

| Factor | Choose G1 | Choose ZGC |
|--------|-----------|------------|
| Pause requirement | < 200ms acceptable | Sub-millisecond required |
| Heap size | 4GB–64GB | Any size; excels at 64GB–16TB |
| Throughput priority | Higher (less overhead) | Slightly lower (~5–15%) |
| Java version | Java 9+ | Java 15+ (prod-ready), Java 21+ for GenZGC |
| Tuning simplicity | Moderate | Minimal — very few flags |
| Memory overhead | Lower | Slightly higher (colored pointers map) |
| CPU | Lower overhead | Higher (concurrent GC threads compete) |

**Decision framework:**
- **Latency SLA > 10ms p99:** G1 is usually sufficient with good tuning
- **Latency SLA < 5ms p99:** ZGC is the right choice
- **Heap > 100GB:** ZGC strongly preferred (G1 can struggle with very large heaps)
- **Financial/trading systems:** ZGC or Shenandoah
- **Batch/throughput-first:** Parallel GC or G1

**Real-world example:**
```bash
# G1 - general-purpose service
-XX:+UseG1GC -Xms4g -Xmx4g -XX:MaxGCPauseMillis=100 -XX:+UseStringDeduplication

# ZGC - low-latency service (Java 21+)
-XX:+UseZGC -Xms8g -Xmx8g
# ZGC self-tunes; minimal flags needed
```

---

## 6. Shenandoah GC

### Q18. How does Shenandoah differ from ZGC? When would you choose Shenandoah over ZGC?

**Answer:**

**Architecture differences:**

| Aspect | Shenandoah | ZGC |
|--------|-----------|-----|
| Origin | Red Hat | Oracle |
| Pointer scheme | Brooks pointer (header forwarding) | Colored pointers (unused address bits) |
| Read barrier | Yes (heavy — checks forwarding ptr) | Yes (load barrier on color check) |
| Generational (2024+) | No (non-generational) | Yes (Generational ZGC since Java 21) |
| Concurrent evacuation | Yes | Yes |
| Heap size | Any | Excels at very large heaps |
| Available in | OpenJDK (not Oracle JDK by default) | OpenJDK & Oracle JDK |

**Brooks Pointer mechanism:**
- Every object has an extra header word pointing to itself (when not relocated) or to the new copy (during relocation)
- Read barrier dereferences this pointer; app threads see the current location
- Higher per-object overhead vs ZGC's colored pointers

**Choose Shenandoah when:**
- Red Hat / IBM distribution is mandated
- Existing Shenandoah-tuned configuration
- Heap sizes where G1's pauses are too high but ZGC isn't available in your distribution

**Choose ZGC when:**
- Oracle JDK is required
- Very large heaps (100GB+)
- Generational collection benefit needed (Java 21+)
- Microsecond-level tail latency is critical

---

## 7. GC Tuning & JVM Flags

### Q19. What are the most important GC tuning flags you use in production and why?

**Answer:**

**Heap sizing (most impactful):**
```bash
-Xms<size>    # Initial heap; set equal to Xmx to avoid resizing pauses
-Xmx<size>    # Maximum heap; leave 25-30% of RAM for OS, direct memory, Metaspace
```

**G1-specific:**
```bash
-XX:+UseG1GC
-XX:MaxGCPauseMillis=200          # Soft pause target (default 200ms)
-XX:G1HeapRegionSize=16m          # Increase for large heaps or humongous objects
-XX:G1NewSizePercent=20           # Min young gen ratio
-XX:G1MaxNewSizePercent=40        # Max young gen ratio
-XX:ConcGCThreads=4               # Concurrent GC thread count
-XX:ParallelGCThreads=8           # STW GC thread count
-XX:+UseStringDeduplication       # Dedup identical strings
-XX:G1MixedGCCountTarget=8        # Number of mixed GC cycles
-XX:G1HeapWastePercent=5          # Tolerate 5% uncollected garbage before stopping mixed GC
```

**ZGC-specific (minimal tuning needed):**
```bash
-XX:+UseZGC
-XX:SoftMaxHeapSize=28g           # Soft max; ZGC returns memory below this
-XX:ZCollectionInterval=1         # Force GC at minimum every 1 second
-XX:ZUncommitDelay=300            # Delay before uncommitting unused memory (seconds)
```

**Metaspace:**
```bash
-XX:MetaspaceSize=256m            # Initial metaspace commit (avoid resize)
-XX:MaxMetaspaceSize=512m         # Cap to catch class loader leaks
```

**GC Logging (essential in production):**
```bash
-Xlog:gc*:file=/logs/gc.log:time,uptime,level,tags:filecount=10,filesize=100m
```

**Ergonomics:**
```bash
-XX:+UseContainerSupport          # Respect cgroup CPU/memory limits (critical in K8s)
-XX:MaxRAMPercentage=75.0         # Set Xmx as % of container memory
```

---

### Q20. How do you determine the right heap size for a Java service in Kubernetes?

**Answer:**

**Step 1: Container awareness**
Java 8u191+ and Java 10+ respect cgroup memory limits with:
```bash
-XX:+UseContainerSupport  # enabled by default Java 11+
-XX:MaxRAMPercentage=75.0
```

**Step 2: Memory budget decomposition**
```
Container Memory Limit (e.g., 4GB)
  - JVM Heap (Xmx):           2.5–3GB  (~65-75% of container)
  - Metaspace:                 256MB
  - Thread Stacks:             ~50MB (100 threads × 512KB)
  - Direct Memory:             512MB (if using NIO)
  - Code Cache:                ~256MB
  - GC overhead:               ~100MB
  ──────────────────────────
  Total off-heap:              ~1.1GB
```

**Step 3: Observe Live Data Set (LDS)**
- Run load test, measure old gen occupancy after Full GC
- Heap should be 2–3× the LDS
- Example: LDS = 800MB → Xmx = 2–2.5GB

**Step 4: GC pause budget**
- Measure p99 GC pause under load
- Tune `-XX:MaxGCPauseMillis` and young gen ratio accordingly

**Step 5: Container resource requests/limits**
```yaml
resources:
  requests:
    memory: "3Gi"
  limits:
    memory: "4Gi"  # JVM flags: -XX:MaxRAMPercentage=75.0 → ~3GB Xmx
```

**Anti-patterns:**
- Setting `requests == limits` AND `-Xms == -Xmx` avoids OOM kills from heap resizing
- Never ignore `-XX:+UseContainerSupport` — without it, JVM sees host RAM, sizes heap to 25% of 256GB

---

### Q21. What is TLAB (Thread-Local Allocation Buffer)? How does it affect allocation performance?

**Answer:**

**Without TLAB:** Every `new Object()` requires CAS (compare-and-swap) on the shared Eden top pointer — contention on multi-core systems.

**With TLAB:**
- Each thread owns a private chunk of Eden (TLAB)
- Allocation within the thread's TLAB is a simple pointer bump — no synchronization
- When TLAB fills, thread requests a new TLAB from Eden
- Objects larger than TLAB threshold allocated directly in Eden (with lock)

**TLAB mechanics:**
```
Eden: [TLAB-T1][TLAB-T2][TLAB-T3][  free  ]
         ↑ ptr bump                  ↑ new TLAB requested here
```

**Tuning (rarely needed — JVM auto-tunes):**
```bash
-XX:TLABSize=512k             # Fixed TLAB size
-XX:+ResizeTLAB               # Default: enabled, auto-resize
-XX:TLABWasteTargetPercent=1  # Max wasted space when TLAB discarded
```

**When TLAB matters:**
- High-throughput allocation apps: TLAB makes allocation nearly free
- If you see `jdk.ObjectAllocationOutsideTLAB` events in JFR, large allocations are bypassing TLAB
- Large objects should go to off-heap or be pooled to avoid TLAB pressure

---

## 8. Memory Leaks & Object Retention

### Q22. What are the most common causes of memory leaks in Java? How do you diagnose them?

**Answer:**

**Common leak patterns:**

1. **Static collection growth:**
```java
static Map<String, byte[]> cache = new HashMap<>();
// Never evicted — grows unboundedly
```

2. **Listener/callback not deregistered:**
```java
eventBus.register(listener); // forgot: eventBus.unregister(listener)
// Listener's transitive object graph is retained
```

3. **ThreadLocal not removed:**
```java
threadLocal.set(largeObject);
// Thread pool: thread reused, ThreadLocal survives
// Fix: threadLocal.remove() in finally block
```

4. **Inner class holding outer reference:**
```java
class Outer {
    class Inner implements Runnable { } // holds implicit reference to Outer
    void startThread() {
        new Thread(new Inner()).start(); // Outer can't be GC'd until thread ends
    }
}
```

5. **Mutable keys in HashMap:**
```java
Map<List<String>, Value> map = new HashMap<>();
List<String> key = new ArrayList<>(Arrays.asList("a"));
map.put(key, value);
key.add("b"); // hashCode changed — entry is now unfindable AND unreachable
```

6. **ClassLoader leaks (in app servers):**
- Redeployment creates new ClassLoader; old one can't be GC'd if static references survive

**Diagnosis process:**

1. **Heap dump:** `jcmd <pid> VM.heap_dump /tmp/heap.hprof`
2. **Analyze with Eclipse MAT or VisualVM:**
   - Look at "Leak Suspects" report
   - Check "Dominator Tree" — which objects retain the most heap
   - Find "Shortest GC Roots Path" to suspect objects
3. **JFR:** Enable `jdk.OldObjectSample` to find long-lived allocation sites
4. **GC logs:** Old gen growing monotonically between Full GCs = leak
5. **JMX:** `java.lang:type=Memory` MBean for trend monitoring

---

### Q23. Explain the difference between strong, soft, weak, and phantom references. Give production use cases.

**Answer:**

**Reference Strength Hierarchy:**
```
Strong > Soft > Weak > Phantom
```

**Strong Reference (default):**
```java
Object obj = new Object(); // strong reference
```
- Object is never GC'd while a strong reference exists

**Soft Reference:**
```java
SoftReference<byte[]> cache = new SoftReference<>(new byte[1024 * 1024]);
```
- GC'd **only when the JVM is low on memory** (before OOM)
- Use case: Memory-sensitive caches (image cache, compiled templates)
- Risk: Can delay OOM, causing GC thrashing before finally collecting

**Weak Reference:**
```java
WeakReference<Widget> ref = new WeakReference<>(widget);
```
- GC'd at the **next GC cycle** when no strong reference exists
- Use case: `WeakHashMap` for canonical maps, listener registries
- `WeakHashMap`: Keys are weakly referenced; entry removed when key GC'd

**Phantom Reference:**
```java
ReferenceQueue<Object> queue = new ReferenceQueue<>();
PhantomReference<Object> ref = new PhantomReference<>(obj, queue);
```
- Enqueued in `ReferenceQueue` **after** object is finalized and reclaimed
- `get()` always returns null
- Use case: **Post-mortem cleanup** (releasing native resources, direct memory)
- Java 9+: Cleaner API (replaces finalize): `Cleaner.create()` uses phantom references internally

**Production patterns:**

| Reference Type | Production Use Case |
|---------------|-------------------|
| Soft | Guava's `CacheBuilder.softValues()` for caching |
| Weak | `WeakHashMap` for metadata attached to objects |
| Phantom | `Cleaner` for native handle cleanup |
| Weak | Dependency injection containers (scope tracking) |

---

### Q24. What is the problem with `finalize()`? What replaced it in modern Java?

**Answer:**

**Problems with `finalize()`:**

1. **Non-deterministic:** No guarantee when (or if) `finalize()` runs
2. **GC overhead:** Finalizable objects survive their first GC — promoted, enqueued in finalizer queue, processed by Finalizer thread
3. **Resurrection risk:** `finalize()` can resurrect an object by storing `this` in a static field
4. **Exception swallowing:** Exceptions in `finalize()` are silently ignored
5. **Thread safety:** `finalize()` runs in a JVM finalizer thread — race conditions possible
6. **Order unpredictable:** No ordering guarantee between finalizable objects
7. **Performance:** Finalizer queue can back up, retaining objects and their graph for longer

**Deprecation timeline:**
- `Object.finalize()` deprecated in **Java 9** (`@Deprecated(since="9")`)
- `finalize()` deprecated for removal in **Java 18** (`@Deprecated(forRemoval=true)`)

**Replacements:**

**1. `java.lang.ref.Cleaner` (Java 9+) — preferred:**
```java
public class NativeResource implements AutoCloseable {
    private static final Cleaner cleaner = Cleaner.create();
    
    private final Cleaner.Cleanable cleanable;
    private final long nativeHandle;
    
    public NativeResource(long handle) {
        this.nativeHandle = handle;
        // State must NOT hold reference to outer object (prevents GC)
        this.cleanable = cleaner.register(this, () -> freeNative(handle));
    }
    
    @Override
    public void close() {
        cleanable.clean(); // explicit close
    }
    
    private static native void freeNative(long handle);
}
```

**2. `try-with-resources` + `AutoCloseable` — for deterministic cleanup:**
```java
try (Connection conn = dataSource.getConnection()) {
    // conn.close() guaranteed
}
```

---

## 9. Metaspace, Off-Heap & Direct Memory

### Q25. What can cause Metaspace to grow unboundedly? How do you diagnose and fix it?

**Answer:**

**Causes:**

1. **ClassLoader leak (most common):**
   - Each classloader's classes live in Metaspace
   - If a ClassLoader is referenced (e.g., via a static field in a class it loaded), it can't be GC'd
   - Common in: OSGi, application servers, plugin systems, dynamic proxying

2. **Dynamic class generation:**
   - Reflection proxies (`Proxy.newProxyInstance`)
   - Lambda metafactories (JVM generates hidden classes)
   - Groovy/Ruby scripts compiled to classes
   - ByteBuddy/cglib/Javassist in excess

3. **Hot redeployment without restart:**
   - Each redeploy creates a new ClassLoader → old classes never unloaded

**Diagnosis:**
```bash
# Monitor Metaspace
jcmd <pid> VM.metaspace

# Native Memory Tracking (expensive, enable early)
java -XX:NativeMemoryTracking=detail
jcmd <pid> VM.native_memory detail

# Heap dump + MAT: look for ClassLoader instances
# JFR: enable class loading events
-XX:StartFlightRecording=settings=profile,filename=profile.jfr
```

**Detection signals:**
- `java.lang.OutOfMemoryError: Metaspace`
- Metaspace growing between full GCs with no corresponding increase in loaded classes
- `jstat -gc <pid>` shows MU (Metaspace Used) always increasing

**Fix:**
- Find and break the ClassLoader retention chain (heap dump analysis)
- Set `-XX:MaxMetaspaceSize=256m` to fail fast rather than exhaust native memory
- Review ClassLoader hierarchy in dynamic systems

---

### Q26. What is off-heap memory in Java? When and why would you use it?

**Answer:**

**Off-heap memory** = memory allocated outside the JVM heap, managed directly (not by GC).

**APIs:**
```java
// Direct ByteBuffer (up to Integer.MAX_VALUE per buffer)
ByteBuffer direct = ByteBuffer.allocateDirect(1024 * 1024 * 1024); // 1GB

// Unsafe (internal, avoid in production)
long addr = Unsafe.getUnsafe().allocateMemory(1024);

// Java 22+: Foreign Memory API (JEP 454, GA)
try (Arena arena = Arena.ofConfined()) {
    MemorySegment segment = arena.allocate(1024);
    // freed when arena closes
}
```

**Reasons to use off-heap:**

| Reason | Explanation |
|--------|-------------|
| Reduce GC pressure | Large data (caches, buffers) doesn't trigger GC |
| I/O performance | `DirectByteBuffer` zero-copy with OS (no heap copy needed) |
| Predictable latency | No GC pauses from large working set |
| Huge data sets | Data larger than practical Xmx (e.g., in-memory databases) |
| Native interop | JNI/JNA — native libraries expect native pointers |

**Production use cases:**
- **Kafka/RocksDB:** Use off-heap for page cache / block cache
- **Netty:** `PooledByteBufAllocator` with direct buffers for network I/O
- **Chronicle Map:** Off-heap map for huge data sets
- **Apache Arrow:** Off-heap columnar data for analytics

**Risk:** No GC safety net. Memory leaks in off-heap are severe and harder to detect. Use `Cleaner` or `try-with-resources` (Foreign Memory API) for deterministic release.

**Direct memory limit:**
```bash
-XX:MaxDirectMemorySize=2g  # Default: same as Xmx; set explicitly
```

---

## 10. Project Loom & Virtual Threads Impact

### Q27. How do virtual threads (Java 21+) affect garbage collection behavior?

**Answer:**

**Virtual thread memory model:**

- Virtual threads are cheap (~1KB initial stack vs ~500KB–1MB for OS threads)
- Stack frames stored on the **heap** as `StackChunk` objects, not in native thread stacks
- A virtual thread carries its stack chunk with it; when parked, the stack is on the heap

**GC implications:**

1. **Stacks become heap objects:** 
   - Stack chunks are normal heap objects — GCed when the virtual thread finishes
   - Millions of parked virtual threads = millions of stack chunk objects on heap
   - G1 and ZGC must handle this additional heap pressure

2. **Larger Young Gen pressure:**
   - Short-lived request-handling virtual threads: create → execute → die
   - Their stack chunks are young gen objects; Minor GC reclaims them quickly
   - Generational GC (G1, GenZGC) benefits here

3. **ZGC Concurrent Thread Stack Scanning (Java 16+):**
   - Platform thread stacks scanned concurrently, not STW
   - Reduces STW pause time proportional to thread count
   - Critical for high-thread-count systems

4. **Stack chunk references:**
   - GC roots must now include heap-allocated stack chunks
   - With millions of virtual threads, root scanning becomes heap scanning
   - G1 and ZGC handle this well; important for STW root scan time

**Tuning for virtual thread-heavy services:**
```bash
# More threads (virtual) → more stack chunks → larger young gen helps
-XX:+UseZGC                    # Best latency with many vthreads
-XX:G1NewSizePercent=30        # If using G1, larger young gen
-Xss512k                       # Platform threads (carriers) can be smaller
```

---

### Q28. With millions of virtual threads, what GC concerns arise and how do you address them?

**Answer:**

**Concern 1: Heap bloat from live virtual threads**
- 1M virtual threads × 2KB average stack = 2GB heap pressure
- Mitigate: Ensure virtual threads complete promptly; don't park them holding large objects

**Concern 2: Increased object promotion rate**
- Each virtual thread's stack chunk may contain references to request objects
- Minor GC must scan all live stack chunks
- Mitigate: Use Generational ZGC for efficient young gen collection

**Concern 3: Pin detection overhead**
- Virtual threads can be "pinned" to carrier threads (inside synchronized, JNI)
- Pinned virtual threads hold a platform thread — reduces scalability
- Java 21 logs pinned threads with `-Djdk.tracePinnedThreads=full`
- Java 24: `synchronized` no longer pins virtual threads (JEP 491)

**Concern 4: ThreadLocal proliferation**
- ThreadLocals unique per virtual thread → potentially millions of entries
- Large ThreadLocal values multiply across all virtual threads
- Mitigate: Use `ScopedValue` (Java 21+) instead of `ThreadLocal` for virtual thread contexts

```java
// Prefer ScopedValue over ThreadLocal in virtual thread contexts
static final ScopedValue<RequestContext> CTX = ScopedValue.newInstance();

ScopedValue.where(CTX, context).run(() -> {
    // CTX.get() works within this scope; no cleanup needed
});
```

---

## 11. Observability: Logs, JFR, JMX

### Q29. How do you set up GC logging in Java 11+ for production? What do you look for?

**Answer:**

**Java 11+ unified logging:**
```bash
-Xlog:gc*:file=/var/log/app/gc.log:time,uptime,level,tags:filecount=10,filesize=50m
```

**Granular configuration:**
```bash
# Essential GC events with timestamps
-Xlog:gc+heap=debug,gc+phases=debug,gc+ergo=debug,safepoint:file=/logs/gc.log:time,uptime:filecount=5,filesize=20m
```

**Key things to monitor:**

1. **Pause time trends:**
   ```
   [gc] GC(42) Pause Young (Normal) (G1 Evacuation Pause) 512M->256M(4096M) 45.678ms
   ```
   Alert if p99 exceeds SLA.

2. **Allocation rate:** `Bytes before → Bytes after` per GC. High allocation rate = more frequent GC.

3. **Promotion failures / Evacuation failures:**
   ```
   [gc] GC(10) Evacuation Failure: 3145728 bytes
   ```
   Precursor to Full GC.

4. **Full GC events:** Should be rare in a well-tuned app.

5. **Concurrent mode failures (G1):**
   ```
   [gc] GC(5) Concurrent Mark Abort
   ```
   Old gen filling faster than concurrent mark can complete.

6. **Humongous allocations:**
   ```
   [gc] GC(3) Pause Young (Concurrent Start) (G1 Humongous Allocation)
   ```

**Tools for analysis:**
- **GCEasy.io:** Paste GC log → visual analysis
- **GCViewer:** Open-source desktop viewer
- **Prometheus + jmx_exporter:** Real-time GC metrics
- **JFR + JDK Mission Control:** Best for deep analysis

---

### Q30. What is JFR (Java Flight Recorder)? How do you use it to diagnose GC problems?

**Answer:**

**JFR** is a low-overhead profiling framework built into the JVM (zero cost when off, ~1–3% overhead when on). Became free/open-source in Java 11.

**Key GC-related JFR event types:**

| Event | What it shows |
|-------|--------------|
| `jdk.GarbageCollection` | Every GC event with duration, cause, type |
| `jdk.GCHeapSummary` | Heap before/after each GC |
| `jdk.OldObjectSample` | Objects that have lived long (leak detection) |
| `jdk.ObjectAllocationInNewTLAB` | Large TLAB allocations |
| `jdk.ObjectAllocationOutsideTLAB` | Allocations bypassing TLAB (large objects) |
| `jdk.AllocationRequiringGC` | Allocations that triggered GC |
| `jdk.PromotionFailed` | Failed young→old promotion |
| `jdk.MetaspaceSummary` | Metaspace usage per GC |
| `jdk.ClassLoaderStatistics` | ClassLoader counts (leak detection) |

**Starting JFR:**
```bash
# At startup
java -XX:StartFlightRecording=duration=60s,filename=recording.jfr,settings=profile MyApp

# Dynamically (production — no restart)
jcmd <pid> JFR.start name=diagnose settings=profile maxage=10m filename=/tmp/recording.jfr
jcmd <pid> JFR.dump name=diagnose filename=/tmp/dump.jfr
jcmd <pid> JFR.stop name=diagnose
```

**Analyzing with JDK Mission Control (JMC):**
1. Open `recording.jfr` in JMC
2. GC tab: pause distribution, heap trend, cause breakdown
3. Memory tab: allocation hotspots (which code path allocates most)
4. Old Object sample: retention paths for long-lived objects

---

## 12. Scenario-Based / Design Questions

### Q31. Your service's GC pauses spiked from 50ms to 500ms after a deployment. How do you diagnose?

**Answer:**

**Systematic investigation:**

**Step 1: Identify what changed**
- New code: large object allocations? New caches? ThreadLocal usage?
- Config: heap size, GC flags, container limits changed?
- Traffic: increased load → increased allocation rate?

**Step 2: GC log analysis**
```bash
# What type of GC is pausing?
grep "Pause" gc.log | grep -v "Young" | head -20
# Is it Full GC? Mixed GC? Evacuation failures?
```

**Step 3: Heap occupancy trend**
- Is Old Gen growing monotonically → leak
- Is allocation rate higher → rate-driven
- Is Old Gen stable but pause is long → compaction overhead

**Step 4: JFR heap allocation**
```bash
jcmd <pid> JFR.start settings=profile duration=60s filename=diag.jfr
```
Check `ObjectAllocationInNewTLAB` — which call sites allocate most?

**Step 5: Common culprits post-deployment:**
- New serialization path allocating large `byte[]` arrays (humongous objects)
- New cache without size limit
- New ORM query returning large result sets
- New library with finalizers increasing finalizer queue depth
- New ThreadLocal holding large request objects

**Resolution path:**
1. If humongous: pool/reuse large arrays, increase `G1HeapRegionSize`
2. If leak: find retention root in heap dump
3. If allocation rate: profile and reduce allocations at hotspot
4. If Old Gen fragmentation: switch from CMS→G1, or tune G1 mixed GC

---

### Q32. Design a Java caching layer that minimizes GC impact for a service handling 100K req/s.

**Answer:**

**Requirements analysis:**
- 100K req/s × even 1KB cached data = 100MB/s allocation pressure if not managed
- GC must not cause tail latency spikes

**Design decisions:**

**1. Off-heap cache for large values:**
```java
// Caffeine with off-heap backing (via Chronicle Map or Caffeine + external store)
Cache<String, byte[]> onHeap = Caffeine.newBuilder()
    .maximumSize(10_000)  // small count, high-frequency "hot" items
    .expireAfterWrite(5, TimeUnit.MINUTES)
    .build();

// Large/cold values in off-heap Chronicle Map
ChronicleMap<String, byte[]> offHeap = ChronicleMap.of(String.class, byte[].class)
    .entries(1_000_000)
    .averageValueSize(1024)
    .createPersistedTo(new File("/cache/data"));
```

**2. Object pooling for reusable structures:**
```java
// Pool request/response objects instead of allocating per-request
ObjectPool<RequestContext> pool = new GenericObjectPool<>(factory);
// Apache Commons Pool or custom ring-buffer pool
```

**3. Arena-style allocation for per-request objects (Java 22+):**
```java
// Foreign Memory API — one arena per request, bulk-free at end
try (Arena arena = Arena.ofConfined()) {
    MemorySegment buffer = arena.allocate(64 * 1024);
    // use buffer for request processing
} // all memory freed at once — no GC needed
```

**4. Avoid large heap caches:**
- Large heap → more GC work per cycle → longer pauses
- Keep heap < 32GB for compressed oops benefit (pointers are 4 bytes, not 8)
- Put cold/large data off-heap

**5. GC selection:**
```bash
-XX:+UseZGC        # sub-ms pauses at 100K req/s
-Xms8g -Xmx8g     # fixed heap, no resize pauses
-XX:MaxDirectMemorySize=16g  # off-heap budget
```

**6. Benchmark + verify with Epsilon GC:**
```bash
# Measure pure allocation overhead
-XX:+UseEpsilonGC -Xmx24g  # will OOM, but shows allocation rate
```

---

### Q33. A Java service running in a 4GB container keeps getting OOMKilled. Walk through your investigation.

**Answer:**

**OOMKill = Linux kernel killed the process for exceeding container memory limit.**

This is NOT a Java OOM — it's a container-level kill.

**Step 1: Understand Java's memory footprint**
```
Total Process RSS = Heap + Metaspace + CodeCache + DirectMemory + ThreadStacks + JVM overhead
```

**Step 2: Check if UseContainerSupport is working**
```bash
# Inside container
java -XX:+PrintFlagsFinal -version | grep "MaxHeapSize\|UseContainerSupport"
# Should show container-aware value, not host RAM-based value
```

**Step 3: Measure actual RSS**
```bash
cat /proc/<pid>/status | grep VmRSS
# Or: jcmd <pid> VM.native_memory summary
```

**Step 4: Common causes in a 4GB container:**

| Cause | Fix |
|-------|-----|
| `-Xmx` not set; JVM uses 25% of host RAM (e.g., 16GB host → 4GB heap) | Set `-XX:MaxRAMPercentage=65.0` |
| Direct memory unbounded | Set `-XX:MaxDirectMemorySize=512m` |
| Metaspace unbounded (class loader leak) | Set `-XX:MaxMetaspaceSize=256m` |
| JIT code cache growing | `-XX:ReservedCodeCacheSize=128m` |
| Too many threads | Reduce thread pool sizes; migrate to virtual threads |
| Off-heap libraries (Netty, Kafka) | Configure their off-heap limits explicitly |

**Step 5: Recommended flags for 4GB container:**
```bash
-XX:+UseContainerSupport
-XX:MaxRAMPercentage=65.0      # ~2.6GB heap
-XX:MaxMetaspaceSize=256m
-XX:MaxDirectMemorySize=512m
-XX:ReservedCodeCacheSize=128m
-XX:+UseZGC                    # Low overhead GC
-Xss256k                       # Smaller stack per thread
```

**Step 6: Monitor with NMT (Native Memory Tracking)**
```bash
java -XX:NativeMemoryTracking=summary
jcmd <pid> VM.native_memory summary scale=MB
```

---

### Q34. How would you handle a situation where your service has 2-minute Full GC pauses every 6 hours?

**Answer:**

**Pattern:** Periodic long Full GC = classic heap saturation or fragmentation.

**Investigation:**

**1. GC log pattern analysis:**
```
# Every 6 hours:
[gc] GC(N) Pause Full (Ergonomics) 3072M->512M(4096M) 120123.456ms
```
- Before GC: 3072M (75% of 4G) — old gen nearly full
- After GC: 512M — lots of garbage was live for 6 hours
- Cause: Ergonomics (G1 could not complete concurrent cycle in time)

**2. Root cause possibilities:**
- **Memory leak:** Objects accumulating for 6 hours, then Full GC partially reclaims
- **Weak/Soft reference batch release:** Caches using SoftRef holding memory until pressure
- **Data that genuinely lives for hours:** Large in-memory aggregations, session stores

**3. Leak vs legitimate retention:**
- Heap dump immediately before Full GC vs immediately after
- What's in Old Gen before the GC that's gone after?
- Track it back to allocation sites via JFR `OldObjectSample`

**4. If it's CMS fragmentation (legacy):**
- Migrate to G1 (concurrent compaction eliminates this)

**5. If it's G1 concurrent mode failure:**
```bash
# Tune IHOP to start collection earlier
-XX:G1ReservePercent=20        # Reserve 20% as safety buffer
-XX:InitiatingHeapOccupancyPercent=35  # Start marking at 35% old gen
-XX:G1MixedGCCountTarget=16   # More mixed GC cycles to clear old gen gradually
```

**6. If it's a genuine workload cycle:**
- Accept the pattern; use ZGC to reduce 2-min pause to sub-ms
- Schedule low-traffic window during the known collection time
- Reduce the 6-hour accumulation via smaller caches or TTL reduction

---

## Quick Reference Cheat Sheet

### GC Selection Guide

```
Need sub-ms pauses?
  YES → ZGC (Java 15+ prod, Java 21+ Generational)
  NO  → Need < 200ms?
          YES → G1GC (default, Java 9+)
          NO  → Need max throughput?
                  YES → Parallel GC (-XX:+UseParallelGC)
                  NO  → Benchmark/testing? → Epsilon GC
```

### Critical JVM Flags Cheat Sheet

```bash
# Heap
-Xms<n>g -Xmx<n>g                    # Set equal to avoid resize
-XX:MaxRAMPercentage=75.0             # K8s: % of container RAM

# GC selection
-XX:+UseG1GC                          # Default Java 9+
-XX:+UseZGC                           # Low-latency (Java 15+ prod)
-XX:+UseShenandoahGC                  # Red Hat alternative to ZGC

# G1 tuning
-XX:MaxGCPauseMillis=200              # Pause target
-XX:G1HeapRegionSize=16m              # For large heaps / humongous objects
-XX:+UseStringDeduplication           # Dedup equal strings

# Metaspace
-XX:MaxMetaspaceSize=512m             # Always cap this

# Logging
-Xlog:gc*:file=/logs/gc.log:time,uptime,level,tags:filecount=10,filesize=50m

# Containers
-XX:+UseContainerSupport              # Respect cgroup limits (default Java 11+)

# Debugging
-XX:NativeMemoryTracking=summary      # Track native memory
-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/tmp/oom.hprof
```

### Version Feature Summary

```
Java  8:  PermGen → Metaspace | G1 available but not default
Java  9:  G1 default | Compact Strings | String deduplication stable
Java 10:  Parallel Full GC for G1
Java 11:  Epsilon GC | ZGC experimental (Linux)
Java 12:  Shenandoah experimental | G1 abortable mixed GC
Java 14:  CMS REMOVED | ZGC on Win/Mac
Java 15:  ZGC + Shenandoah PRODUCTION READY
Java 16:  ZGC concurrent thread stack scanning
Java 21:  Generational ZGC experimental | Virtual Threads GA
Java 23:  Generational ZGC default
Java 25:  Generational ZGC mature | Virtual Threads full ecosystem
```
