# Java Threads & Concurrency — Experienced Interview Q&A (10–15 Years)
> Sourced from real interviews at Google, Amazon, JP Morgan, Goldman Sachs, Uber, Flipkart, Atlassian, Razorpay, Oracle.
> Focus: practical scenarios, internals, production debugging, coding questions.

---

## Table of Contents

1. [Thread Lifecycle & Internals](#1-thread-lifecycle--internals)
2. [synchronized — Monitor, Locks, Reentrancy](#2-synchronized--monitor-locks-reentrancy)
3. [wait / notify / notifyAll — Condition Queues](#3-wait--notify--notifyall--condition-queues)
4. [volatile vs synchronized — JMM Depth](#4-volatile-vs-synchronized--jmm-depth)
5. [Deadlock, Livelock, Starvation](#5-deadlock-livelock-starvation)
6. [ThreadPoolExecutor Internals](#6-threadpoolexecutor-internals)
7. [ReentrantLock, ReadWriteLock, StampedLock](#7-reentrantlock-readwritelock-stampedlock)
8. [Atomic Classes, CAS, ABA, False Sharing](#8-atomic-classes-cas-aba-false-sharing)
9. [BlockingQueue Variants](#9-blockingqueue-variants)
10. [CountDownLatch, CyclicBarrier, Semaphore, Phaser, Exchanger](#10-countdownlatch-cyclicbarrier-semaphore-phaser-exchanger)
11. [CompletableFuture — Deep Dive](#11-completablefuture--deep-dive)
12. [Fork/Join Framework](#12-forkjoin-framework)
13. [ThreadLocal — Patterns & Memory Leaks](#13-threadlocal--patterns--memory-leaks)
14. [Virtual Threads (Java 21+) & Structured Concurrency](#14-virtual-threads-java-21--structured-concurrency)
15. [Practical Coding Scenarios](#15-practical-coding-scenarios)
16. [Production Debugging & Observability](#16-production-debugging--observability)
17. [Rapid-Fire Gotchas](#17-rapid-fire-gotchas)

---

## 1. Thread Lifecycle & Internals

### Q1. What are all the thread states in Java and what JVM event causes each transition?

Java defines 6 thread states in `Thread.State` enum. These are JVM-level states, not OS-level states.

```
                    ┌─────────────────────────────────────────┐
                    │                                         │
  NEW ──start()──► RUNNABLE ◄───────────────────────────────┐│
                      │                                      ││
              blocking I/O  ──────────────► BLOCKED          ││
              synchronized                 (waiting for      ││
                                           monitor lock)     ││
              Object.wait()                                  ││
              Thread.join() ──────────────► WAITING          ││
              LockSupport.park()           (indefinitely)    ││
                                                             ││
              sleep(ms)                                      ││
              wait(ms)        ──────────── TIMED_WAITING     ││
              join(ms)                                       ││
              parkNanos(ns)                                  ││
                      │                                      ││
              run() returns                                  ││
              uncaught exception ──────── TERMINATED         ││
                                                             ││
└────────────────────────────────────────────────────────────┘│
```

**Critical distinction often missed in interviews:**

| State | What it means |
|-------|--------------|
| `BLOCKED` | Waiting to acquire an **intrinsic lock** (`synchronized`). OS-scheduled out. |
| `WAITING` | Voluntarily relinquished CPU — waiting for an explicit `notify()`, `join()`, or `unpark()`. |
| `TIMED_WAITING` | Same as WAITING but with a timeout — auto-resumes after deadline. |

**BLOCKED vs WAITING:** A thread inside `synchronized` waiting for the lock = `BLOCKED`. A thread inside `synchronized` that called `wait()` = `WAITING`. This distinction matters for deadlock analysis in thread dumps.

---

### Q2. What is the difference between a daemon thread and a user thread? Practical impact?

```java
Thread t = new Thread(() -> {
    while (true) {
        doBackgroundWork();
        Thread.sleep(1000);
    }
});
t.setDaemon(true); // must be called BEFORE start()
t.start();

// When all user threads finish:
// - Daemon threads are terminated immediately by the JVM
// - No finally blocks in daemon threads are guaranteed to run
// - JVM exits
```

**Production impact:**

```java
// BUG: Background executor with default (user) threads keeps JVM alive forever
ExecutorService executor = Executors.newSingleThreadExecutor();
executor.submit(() -> { /* background task */ });
// Main method returns — JVM does NOT exit. Process hangs.

// Fix 1: Shutdown the executor
executor.shutdown();

// Fix 2: Daemon thread factory
ExecutorService executor = Executors.newSingleThreadExecutor(r -> {
    Thread t = new Thread(r);
    t.setDaemon(true);
    return t;
});
// Now JVM exits when main thread ends
```

**Daemon threads cannot replace graceful shutdown.** Use them only for tasks that are safe to abandon at any point (background metrics, heartbeats, cache warmers).

---

### Q3. Why is `Thread.stop()` deprecated? What is the correct interruption protocol?

**Why `stop()` is dangerous:**
- Throws `ThreadDeath` (an `Error`) from whatever line the thread is executing
- Releases ALL held monitors immediately — leaves shared data in a **partially-updated, inconsistent state**
- The thread releasing the lock may have been halfway through a compound update

**Correct interruption protocol:**

```java
// Pattern 1: Cooperative flag for non-blocking tasks
class WorkerTask implements Runnable {
    private volatile boolean cancelled = false;

    public void cancel() { cancelled = true; }

    @Override
    public void run() {
        while (!cancelled) {
            processNextItem();
        }
    }
}

// Pattern 2: Thread.interrupt() for blocking tasks
class BlockingWorker implements Runnable {
    @Override
    public void run() {
        try {
            while (!Thread.currentThread().isInterrupted()) {
                String item = blockingQueue.take(); // throws InterruptedException when interrupted
                process(item);
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt(); // restore the interrupt flag — CRITICAL
            // clean up resources...
        }
    }
}

// Pattern 3: Responding to interrupt in a long CPU-bound loop
void compute() {
    for (int i = 0; i < LARGE_NUMBER; i++) {
        if (Thread.interrupted()) {  // clears the flag — check it at checkpoints
            throw new InterruptedException();
        }
        heavyComputation(i);
    }
}
```

**Golden rule:** Always restore the interrupt flag with `Thread.currentThread().interrupt()` when catching `InterruptedException` — unless you're the top-level handler. Swallowing it silently breaks the cooperative cancellation chain.

---

### Q4. What does `Thread.interrupt()` do when the thread is in each state?

| Thread State | Effect of `interrupt()` |
|-------------|------------------------|
| `RUNNABLE` | Sets the **interrupted flag** (`isInterrupted()` → true). Thread must check it manually. |
| `WAITING` / `TIMED_WAITING` (via `sleep`, `wait`, `join`) | **Immediately** throws `InterruptedException` and **clears** the flag. |
| `BLOCKED` (waiting for synchronized lock) | Sets the flag but thread remains BLOCKED — interrupt does NOT free it from a monitor wait. |
| NIO blocking I/O (`SocketChannel.read()`) | Throws `ClosedByInterruptException`, closes the channel. |
| Classic blocking I/O (`InputStream.read()`) | **No effect** on most platforms. The thread stays blocked. |

**Key insight for investment bank interviews:** Classic blocking socket I/O (`Socket.getInputStream().read()`) cannot be interrupted. The fix is `socket.close()` from another thread — which throws `SocketException` in the blocked thread.

---

## 2. synchronized — Monitor, Locks, Reentrancy

### Q5. Explain the intrinsic lock / monitor. What are the three regions of a Java object monitor?

Every Java object has an associated **monitor** (also called the intrinsic lock or object lock). The monitor has three regions:

```
┌─────────────────────────────────┐
│         Java Object Monitor     │
│                                 │
│  Entry Set: threads BLOCKED     │
│  waiting for the lock           │
│  ─────────────────────          │
│  Owner: the thread holding      │
│  the lock (one at a time)       │
│  ─────────────────────          │
│  Wait Set: threads that called  │
│  wait() — will re-enter entry   │
│  set when notified              │
└─────────────────────────────────┘
```

1. **Entry Set**: Threads competing to acquire the lock → `BLOCKED` state
2. **Owner**: The single thread that holds the lock → `RUNNABLE`
3. **Wait Set**: Threads that called `wait()` → `WAITING` state (lock released while here)

When `notify()` is called, one thread moves from **Wait Set → Entry Set** (not directly to Owner). It still has to compete for the lock.

---

### Q6. What is the difference between object lock and class lock? Can they run concurrently?

```java
class Counter {
    private int count = 0;

    // Acquires lock on THIS instance
    public synchronized void increment() { count++; }

    // Acquires lock on Counter.class object
    public static synchronized int getInstanceCount() { return instanceCount; }
}

// Two different locks — they do NOT block each other:
Counter c = new Counter();
// Thread 1: c.increment()          → acquires lock on c (the instance)
// Thread 2: Counter.getInstanceCount() → acquires lock on Counter.class
// They run CONCURRENTLY — separate monitors
```

**Common bug pattern:**
```java
class BankAccount {
    private double balance;

    public synchronized void deposit(double amount) {
        balance += amount; // locks on `this`
    }

    public static synchronized void transfer(BankAccount from, BankAccount to, double amount) {
        // locks on BankAccount.class — NOT on from or to instances
        // deposit() inside here re-acquires instance lock — different from class lock
        // two threads calling deposit() can interleave with transfer() ← BUG
    }
}
```

---

### Q7. What is lock reentrancy? Why does Java need it?

```java
class ReentrantDemo {
    public synchronized void outer() {
        System.out.println("outer");
        inner(); // same thread, same lock — would deadlock without reentrancy
    }

    public synchronized void inner() {
        System.out.println("inner");
    }
}
```

Java's intrinsic locks (and `ReentrantLock`) track an **acquisition count**:
- Thread acquires lock → count = 1
- Same thread re-enters → count = 2
- Exits inner block → count = 1
- Exits outer block → count = 0 → lock released

**Without reentrancy:** A synchronized method calling another synchronized method on the same object would deadlock with itself. This is why every real OO language's lock is reentrant.

---

### Q8. Can a synchronized instance method and a synchronized static method run concurrently?

**Yes.** They use different monitors:

```java
class Foo {
    synchronized void instanceMethod() {
        Thread.sleep(5000); // holds lock on `this`
    }

    static synchronized void staticMethod() {
        Thread.sleep(5000); // holds lock on Foo.class
    }
}

Foo foo = new Foo();
// Thread A: foo.instanceMethod()  → acquires foo's monitor
// Thread B: Foo.staticMethod()    → acquires Foo.class monitor
// Both run simultaneously — no blocking
```

This is a common interview trick question.

---

## 3. wait / notify / notifyAll — Condition Queues

### Q9. Why must `wait()`, `notify()`, `notifyAll()` be called inside `synchronized`?

`wait()` does two things atomically:
1. **Releases** the object monitor
2. Moves the thread to the **Wait Set** (WAITING state)

These two must happen atomically. If `wait()` could be called without holding the monitor:
- Another thread could call `notify()` between the condition check and `wait()` — **missed wakeup**
- Releasing a monitor you don't hold is meaningless

Java enforces this by throwing `IllegalMonitorStateException` if called without the monitor.

```java
synchronized (lock) {         // MUST hold the lock
    while (!conditionMet()) { // ALWAYS a while loop (not if)
        lock.wait();          // atomically: release lock + enter wait set
    }
    // Condition is true here, lock re-acquired
    doWork();
}
```

---

### Q10. What is a spurious wakeup? How do you defend against it?

A **spurious wakeup** is when a thread in `wait()` wakes up even though no `notify()` or `notifyAll()` was called. This is allowed by the POSIX pthread spec and by the JVM spec. It happens due to OS-level signal handling on some platforms (Linux in particular).

```java
// WRONG — vulnerable to spurious wakeup:
synchronized (lock) {
    if (!conditionMet()) {   // if: checked only once
        lock.wait();
    }
    // Thread woke up spuriously — condition may still be false!
    process(); // BUG: processing when not ready
}

// CORRECT — always loop:
synchronized (lock) {
    while (!conditionMet()) { // while: re-checks after every wakeup
        lock.wait();
    }
    process(); // condition is GUARANTEED true here
}
```

**Interview flag:** Using `if` instead of `while` around `wait()` is an immediate red flag in Amazon and Google interviews. It's question #1 in concurrency coding rounds.

---

### Q11. When should you use `notifyAll()` instead of `notify()`?

**`notify()` wakes ONE arbitrary thread** from the wait set. Safe ONLY when:
1. All waiting threads are waiting on the **same condition**
2. **Any one** of them would make progress

**`notifyAll()` wakes ALL waiting threads.** They all compete to re-acquire the lock; each re-checks its condition; only those that find it satisfied proceed.

```java
// Dangerous use of notify() — multiple conditions, one lock:
synchronized (queue) {
    queue.offer(item);
    queue.notify(); // might wake a producer (also waiting on queue.isEmpty())
                   // instead of a consumer — missed wakeup
}

// Safe: notifyAll() or better — separate Condition objects (ReentrantLock)
synchronized (queue) {
    queue.offer(item);
    queue.notifyAll(); // guarantees a consumer wakes up
}

// Best: ReentrantLock with separate Conditions
lock.lock();
try {
    queue.offer(item);
    notEmpty.signal(); // signals ONLY consumers waiting on notEmpty
} finally { lock.unlock(); }
```

**Performance:** `notifyAll()` causes a **thundering herd** — all threads wake, all compete, only one wins. For high-throughput producer-consumer, use `ReentrantLock` with two separate `Condition` objects.

---

## 4. volatile vs synchronized — JMM Depth

### Q12. What does `volatile` guarantee? What does it NOT guarantee? Prove with examples.

**Guarantees:**
1. **Visibility**: Every write to a volatile field is immediately flushed to main memory. Every read goes to main memory (not a CPU cache).
2. **Ordering**: Prevents instruction reordering across the volatile access (memory barrier).

**Does NOT guarantee:**
- **Atomicity** of compound operations

```java
volatile int counter = 0;

// Thread 1 & Thread 2 both execute:
counter++; // Read (1) + Increment (2) + Write (3) — NOT atomic

// Lost update scenario:
// T1 reads: counter = 5
// T2 reads: counter = 5
// T1 writes: counter = 6
// T2 writes: counter = 6  ← lost T1's increment
// Expected: 7. Got: 6.

// Fix: AtomicInteger
AtomicInteger counter = new AtomicInteger(0);
counter.incrementAndGet(); // CAS — atomic
```

**64-bit visibility guarantee (often missed):**
```java
// On 32-bit JVMs, reading/writing long and double is NOT atomic without volatile
// Two 32-bit operations for one 64-bit value — can see a "torn read"
volatile long timestamp = 0; // guaranteed atomic read/write on all JVMs
```

---

### Q13. Explain the JMM memory barriers inserted by `volatile`.

On x86, every volatile write compiles to a regular store + `LOCK ADD [rsp], 0` (full memory fence). Volatile read on x86 is typically a plain load (x86 has strong memory ordering).

**JVM memory barrier semantics:**

```
Volatile WRITE:
  [StoreStore barrier] ← prevents prior stores from being reordered past volatile write
  WRITE to volatile field
  [StoreLoad barrier] ← prevents volatile write from being reordered past subsequent loads
  (most expensive barrier — full fence)

Volatile READ:
  READ from volatile field
  [LoadLoad barrier] ← prevents subsequent loads from being seen before volatile read
  [LoadStore barrier] ← prevents subsequent stores from being moved before volatile read
```

**Practical implication:**
```java
int data = 0;
volatile boolean ready = false;

// Thread 1:
data = 42;      // guaranteed to be visible to Thread 2 BEFORE ready = true
ready = true;   // volatile write → StoreStore barrier above this

// Thread 2:
if (ready) {    // volatile read → LoadLoad barrier after this
    System.out.println(data); // guaranteed to see 42
}
```

---

### Q14. Describe all the sources of happens-before ordering in the JMM.

| HB Rule | Meaning |
|---------|---------|
| **Program Order** | Within a single thread, each statement HB the next |
| **Monitor Unlock → Lock** | `unlock()` HB the next `lock()` on the same monitor |
| **Volatile Write → Read** | Write to a volatile field HB every subsequent read of that field |
| **Thread.start()** | Everything before `start()` in the parent HB any action in the child thread |
| **Thread.join()** | All actions in thread T HB the return of `T.join()` |
| **Thread Interruption** | `interrupt()` call HB the interrupted thread detecting the interrupt |
| **Object Finalizer** | End of constructor HB start of `finalize()` |
| **Static Initializer** | Completion of static initializer HB first use of the class |
| **Transitivity** | A HB B and B HB C → A HB C |

**Practical safe publication patterns** (all exploit HB rules):
```java
// 1. volatile field (volatile write HB read)
private volatile Data data;
void publish() { data = new Data(); }

// 2. static initializer (class init HB first use)
static final Data data = new Data(); // safely published

// 3. synchronized (unlock HB lock)
private Data data;
synchronized void publish() { data = new Data(); }

// 4. final fields (constructor completion HB any thread seeing the ref)
class SafeData { final int x; SafeData(int x) { this.x = x; } }
```

---

### Q15. The Double-Checked Locking (DCL) problem — what is broken and what is the fix?

**Broken DCL (without volatile — broken even in Java 5+):**
```java
class Singleton {
    private static Singleton instance; // NOT volatile

    public static Singleton getInstance() {
        if (instance == null) {           // Check 1 — no lock
            synchronized (Singleton.class) {
                if (instance == null) {   // Check 2 — with lock
                    instance = new Singleton(); // 3 steps, can be reordered
                }
            }
        }
        return instance;
    }
}
```

`instance = new Singleton()` compiles to roughly:
1. Allocate memory
2. Initialize fields (constructor body)
3. Assign reference to `instance`

**JIT/CPU may reorder steps 2 and 3**: another thread reads a non-null `instance` but sees uninitialized fields (e.g., `null` fields that should have values).

**Fix — `volatile` prevents reordering:**
```java
private static volatile Singleton instance;
// volatile write on step 3 creates StoreStore barrier before it
// guarantees 1 → 2 → 3 order
```

**Better — Initialization-On-Demand Holder (no volatile, no sync cost):**
```java
class Singleton {
    private Singleton() {}
    private static class Holder {
        static final Singleton INSTANCE = new Singleton();
        // Class loading is guaranteed single-threaded by JVM spec
        // Holder loaded lazily on first access to INSTANCE
    }
    public static Singleton getInstance() { return Holder.INSTANCE; }
}
```

**Best for singletons — enum (also serialization-safe, reflection-safe):**
```java
public enum Singleton { INSTANCE; }
```

---

## 5. Deadlock, Livelock, Starvation

### Q16. Code a minimal deadlock. Explain the four Coffman conditions.

```java
class DeadlockDemo {
    static final Object lockA = new Object();
    static final Object lockB = new Object();

    public static void main(String[] args) {
        Thread t1 = new Thread(() -> {
            synchronized (lockA) {
                sleep(100); // give t2 time to acquire lockB
                synchronized (lockB) { System.out.println("T1 done"); }
            }
        });

        Thread t2 = new Thread(() -> {
            synchronized (lockB) {       // t2 holds B, wants A
                synchronized (lockA) { System.out.println("T2 done"); }
            }
        });
        t1.start(); t2.start();
        // DEADLOCK: T1 holds A waiting for B, T2 holds B waiting for A
    }
}
```

**Four Coffman Conditions (ALL must hold for deadlock):**

| Condition | Description | How to break it |
|-----------|-------------|----------------|
| **Mutual Exclusion** | Resource can't be shared | Not always possible (locks are exclusive) |
| **Hold and Wait** | Thread holds a resource while waiting for another | Acquire all locks atomically or none |
| **No Preemption** | Resources can't be forcibly taken | Use `tryLock(timeout)` to abandon locks |
| **Circular Wait** | Circular chain of waiting threads | **Always acquire locks in a globally consistent order** |

**Production fix — lock ordering:**
```java
// Always acquire the lock with lower System.identityHashCode first:
void transfer(Account from, Account to, double amount) {
    Account first  = from.id < to.id ? from : to;
    Account second = from.id < to.id ? to : from;
    synchronized (first) {
        synchronized (second) {
            from.balance -= amount;
            to.balance   += amount;
        }
    }
}
```

---

### Q17. How do you detect a deadlock in a running production JVM?

**Method 1 — jstack (instant, no agent required):**
```bash
jstack <pid>
# Output includes:
# Found one Java-level deadlock:
# "Thread-1" waiting to lock monitor 0x...
# which is held by "Thread-0"
# "Thread-0" waiting to lock monitor 0x...
# which is held by "Thread-1"
```

**Method 2 — Programmatic detection (runtime monitoring):**
```java
ThreadMXBean tmx = ManagementFactory.getThreadMXBean();
long[] deadlocked = tmx.findDeadlockedThreads(); // returns null if none
if (deadlocked != null) {
    ThreadInfo[] info = tmx.getThreadInfo(deadlocked);
    // alert, take heap dump, etc.
}
```

**Method 3 — JFR (Java Flight Recorder):**
```bash
jcmd <pid> JFR.start settings=default duration=60s filename=deadlock.jfr
# JMC can display BLOCKED thread chains visually
```

**Method 4 — APM Alerts:**
- Sudden spike in BLOCKED threads in Datadog / New Relic
- BLOCKED thread count metric via `jmx_exporter` + Prometheus

---

### Q18. What is livelock? How is it different from deadlock? How do you diagnose it?

**Livelock:** Threads are actively running and reacting to each other but making NO progress.

```java
// Classic hallway problem in code:
class Philosopher {
    private Lock fork1, fork2;

    void eat() {
        while (true) {
            if (fork1.tryLock()) {
                if (fork2.tryLock()) {
                    // eat
                    fork2.unlock(); fork1.unlock();
                    return;
                }
                fork1.unlock(); // politely release, try again
            }
            // Both philosophers release at exactly the same time
            // and retry at exactly the same time → infinite loop
        }
    }
}
```

**Deadlock vs Livelock:**

| Aspect | Deadlock | Livelock |
|--------|----------|----------|
| Thread state | BLOCKED (visible in jstack) | RUNNABLE (burning CPU) |
| Activity | None | High — threads are responding |
| Progress | None | None |
| Detection | jstack shows BLOCKED chains | CPU pegged but throughput = 0 |
| Fix | Lock ordering / tryLock with timeout | **Randomized exponential backoff** |

**Diagnosis:** Livelock does NOT show up as BLOCKED threads in a thread dump. Look for:
- CPU near 100% but throughput metric at 0
- Profiler hotspot pointing to a retry/backoff loop

**Fix — randomized backoff:**
```java
Random rng = new Random();
int backoffMs = 10;
while (true) {
    if (fork1.tryLock(backoffMs, MILLISECONDS)) {
        if (fork2.tryLock(backoffMs, MILLISECONDS)) {
            eat(); fork2.unlock(); fork1.unlock(); return;
        }
        fork1.unlock();
    }
    // Randomized sleep prevents synchronized retries
    Thread.sleep(rng.nextInt(backoffMs));
    backoffMs = Math.min(backoffMs * 2, 1000); // exponential cap
}
```

---

### Q19. What causes thread starvation? When does `ReentrantLock(true)` help — and when does it hurt?

**Starvation:** A thread is perpetually denied the CPU/lock because other threads always get priority.

```java
// Unfair lock — default for both synchronized and ReentrantLock:
// High-priority threads or threads that happen to be scheduled at the right moment
// repeatedly "barge in" — a waiting low-priority thread may never get the lock.

// Fair lock — FIFO ordering:
ReentrantLock fairLock = new ReentrantLock(true); // fairness = true
// Threads acquire in the order they first requested the lock
```

**When fair lock helps:** Long-running services where each request must be served eventually. Payment processing where some transactions could starve indefinitely.

**When fair lock hurts:**
- **30–50% lower throughput** due to extra context switches
- FIFO prevents the JVM from using a "currently scheduled thread" optimization
- Under high contention, throughput drops dramatically

**Better starvation solutions than fair locks:**
- Increase thread pool size
- Partition resources (one lock per user/segment)
- Work-stealing queues (ForkJoinPool)
- Rate limiting at the entry point

---

## 6. ThreadPoolExecutor Internals

### Q20. Walk through the full task submission flow in ThreadPoolExecutor.

```
Task submitted to ThreadPoolExecutor.execute(task)
│
├── Running threads < corePoolSize?
│       YES → Create a new CORE thread to run this task
│             (even if idle threads exist — counterintuitive)
│
├── Running threads >= corePoolSize → Try to queue the task
│       Queue.offer(task) returns true?
│             YES → Task is queued
│                   Double-check: pool still running?
│                   If no → remove from queue, reject
│                   If yes → running threads == 0? Add thread.
│
│       Queue.offer(task) returns FALSE (queue full)
│
├── Running threads < maximumPoolSize?
│       YES → Create a new NON-CORE thread to run this task
│             (keepAliveTime applies — idle non-core threads are reaped)
│
└── Running threads >= maximumPoolSize AND queue full
        → invoke RejectedExecutionHandler
```

**The critical gotcha:**
```java
// Executors.newFixedThreadPool(10) uses an UNBOUNDED LinkedBlockingQueue
// → step "queue full" NEVER happens
// → maximumPoolSize is irrelevant — always 10 threads maximum
// → under overload: unbounded task accumulation → OOM

// Correct bounded config for production:
ThreadPoolExecutor executor = new ThreadPoolExecutor(
    10,           // corePoolSize
    50,           // maximumPoolSize  ← only reached when queue is full
    60, SECONDS,  // keepAliveTime for non-core threads
    new ArrayBlockingQueue<>(1000),   // BOUNDED queue ← triggers max pool growth
    new CallerRunsPolicy()            // backpressure on overload
);
```

---

### Q21. Explain all four rejection policies. When would you use each in production?

```java
// 1. AbortPolicy (DEFAULT)
new ThreadPoolExecutor.AbortPolicy()
// Throws RejectedExecutionException
// Use: when the caller must know about rejection (can catch and retry/alert)

// 2. CallerRunsPolicy
new ThreadPoolExecutor.CallerRunsPolicy()
// Runs the task in the CALLING thread
// Natural backpressure: slows down the producer while the pool catches up
// Use: batch jobs, event loops where you want to slow ingestion, not drop tasks

// 3. DiscardPolicy
new ThreadPoolExecutor.DiscardPolicy()
// Silently drops the rejected task. No exception.
// Use: metrics sampling, fire-and-forget logging, periodic health checks
// Never use: for financial transactions or critical data

// 4. DiscardOldestPolicy
new ThreadPoolExecutor.DiscardOldestPolicy()
// Removes the OLDEST task from the queue and retries submission
// Use: cache refresh tasks where latest is always more relevant than queued
// Risk: the discarded old task may be essential — use only for idempotent updates

// Custom policy (production-grade):
executor.setRejectedExecutionHandler((task, pool) -> {
    if (!pool.isShutdown()) {
        metrics.increment("task.rejected");
        alerting.warn("Thread pool saturated");
        try {
            pool.getQueue().put(task); // block caller until space available
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
});
```

---

### Q22. Why does `Executors.newCachedThreadPool()` use `SynchronousQueue`?

```java
// SynchronousQueue has ZERO capacity:
// offer(task) returns false immediately if no thread is waiting
// put(task) blocks until a thread calls take()

// CachedThreadPool behavior:
// 1. Task arrives → offer to SynchronousQueue
// 2. No idle thread waiting → offer returns false
// 3. ThreadPoolExecutor: queue full + threads < maxPoolSize(Integer.MAX_VALUE)
//    → create a new thread
// 4. New thread takes the task from the SynchronousQueue (direct handoff)

// This achieves: a new thread for EVERY task that arrives when all threads are busy
// The pool grows unboundedly under burst load
```

**Production danger:**
```java
// A sudden burst of 100,000 tasks creates 100,000 threads
// Each thread: 512KB-1MB stack → 50-100GB RAM → OOM or OS thread limit hit

// Safe alternative for bursty workloads:
ExecutorService executor = new ThreadPoolExecutor(
    0, 200,              // 0 core, 200 max (bounded)
    60, SECONDS,
    new SynchronousQueue<>()   // still direct handoff
);
// → Bounded to 200 threads, rejects if all busy
```

---

### Q23. What is the difference between `execute()` and `submit()`?

```java
// execute(Runnable) — fire and forget
executor.execute(() -> {
    throw new RuntimeException("I failed silently");
    // Exception goes to UncaughtExceptionHandler — caller has no way to know
});

// submit(Callable<T>) — returns a Future
Future<String> future = executor.submit(() -> {
    throw new RuntimeException("I failed");
    // Exception stored in Future — re-thrown when future.get() is called
});
try {
    String result = future.get(); // throws ExecutionException wrapping RuntimeException
} catch (ExecutionException e) {
    Throwable cause = e.getCause(); // the original RuntimeException
}

// submit(Runnable) — returns Future<?> with null result
Future<?> f = executor.submit(() -> doWork());
f.get(); // blocks until done; throws ExecutionException if Runnable threw
```

**Production rule:** Always use `submit()` for error visibility. Install an `UncaughtExceptionHandler` as a last resort safety net:
```java
ThreadFactory factory = r -> {
    Thread t = new Thread(r);
    t.setUncaughtExceptionHandler((thread, ex) -> log.error("Uncaught in {}", thread.getName(), ex));
    return t;
};
```

---

### Q24. How do you correctly shut down an `ExecutorService`? What is the risk of `shutdownNow()`?

```java
// Graceful shutdown (production-standard pattern):
executor.shutdown(); // stops accepting new tasks, drains the queue

try {
    if (!executor.awaitTermination(30, TimeUnit.SECONDS)) {
        log.warn("Executor did not terminate in 30s, forcing shutdown");
        List<Runnable> unstarted = executor.shutdownNow(); // interrupt running tasks
        log.warn("Unstarted tasks: {}", unstarted.size());

        if (!executor.awaitTermination(10, TimeUnit.SECONDS)) {
            log.error("Executor still not terminated — possible thread leak");
        }
    }
} catch (InterruptedException e) {
    executor.shutdownNow();
    Thread.currentThread().interrupt();
}
```

**`shutdownNow()` risks:**
- Calls `Thread.interrupt()` on each running thread
- Tasks that don't check `isInterrupted()` or catch `InterruptedException` run to completion
- Returns the list of queued tasks that were never started (for manual reprocessing)
- Does NOT guarantee running tasks are stopped — just requests interruption

---

## 7. ReentrantLock, ReadWriteLock, StampedLock

### Q25. When should you choose `ReentrantLock` over `synchronized`? Be specific.

```java
// Use ReentrantLock when you need:

// 1. tryLock() — non-blocking acquisition attempt
if (lock.tryLock(200, MILLISECONDS)) {
    try { process(); }
    finally { lock.unlock(); }
} else {
    // Handle contention: return, retry, alert — can't do this with synchronized
}

// 2. lockInterruptibly() — respond to interruption while waiting for lock
lock.lockInterruptibly(); // throws InterruptedException if interrupted while BLOCKED
// synchronized: thread stays BLOCKED even when interrupted

// 3. Fairness
ReentrantLock fair = new ReentrantLock(true); // FIFO ordering

// 4. Multiple Condition queues (see Q11 example)
Condition notFull  = lock.newCondition();
Condition notEmpty = lock.newCondition();

// 5. Lock monitoring (diagnostic)
System.out.println(lock.getQueueLength());  // # threads waiting
System.out.println(lock.isHeldByCurrentThread());
```

**When to stick with `synchronized`:**
- JIT optimizes it aggressively (lock elision, lock coarsening, biased locking)
- Cannot forget to unlock (compiler ensures it)
- Simpler code
- 95% of use cases — prefer `synchronized` unless you need one of the above features

---

### Q26. Explain `ReadWriteLock` — when is it better than `synchronized`?

```java
ReadWriteLock rwLock = new ReentrantReadWriteLock();
Lock readLock  = rwLock.readLock();
Lock writeLock = rwLock.writeLock();

// Multiple readers can hold the read lock simultaneously
// Writer requires EXCLUSIVE access — blocks all readers and other writers

// In-memory cache example:
class ReadHeavyCache<K, V> {
    private final Map<K, V> map = new HashMap<>();
    private final ReadWriteLock lock = new ReentrantReadWriteLock();

    public V get(K key) {
        lock.readLock().lock();
        try { return map.get(key); }
        finally { lock.readLock().unlock(); }
    }

    public void put(K key, V value) {
        lock.writeLock().lock();
        try { map.put(key, value); }
        finally { lock.writeLock().unlock(); }
    }
}
// 1000 concurrent reads → all proceed simultaneously
// 1 write → waits for all reads to finish, then gets exclusive access
```

**Can you upgrade a read lock to a write lock?**
```java
// DEADLOCK — DO NOT DO THIS:
readLock.lock();
// ...
writeLock.lock(); // blocks forever: waiting for all readers to release
                  // but this thread IS a reader holding the read lock
readLock.unlock(); // never reached
```

Solution: Release read lock, then acquire write lock (check condition again — may have changed):
```java
readLock.lock();
try {
    if (needsUpdate()) {
        readLock.unlock(); // release first
        writeLock.lock();
        try {
            // re-check condition since another thread may have updated
            if (needsUpdate()) update();
        } finally { writeLock.unlock(); }
        readLock.lock(); // re-acquire read lock if needed
    }
} finally { readLock.unlock(); }
```

---

### Q27. What is `StampedLock`? How does optimistic reading work and what makes it dangerous?

`StampedLock` (Java 8) adds a third mode: **optimistic read** — no lock acquired at all.

```java
StampedLock sl = new StampedLock();
double x, y; // shared mutable state

// Optimistic read — NO lock acquisition:
void distance() {
    long stamp = sl.tryOptimisticRead(); // returns a stamp (non-zero if no writer active)
    double curX = x; // read without lock
    double curY = y; // read without lock

    if (!sl.validate(stamp)) { // did a writer intervene?
        // Yes — fall back to a real read lock:
        stamp = sl.readLock();
        try {
            curX = x;
            curY = y;
        } finally { sl.unlockRead(stamp); }
    }
    return Math.sqrt(curX * curX + curY * curY);
}

void move(double newX, double newY) {
    long stamp = sl.writeLock();
    try { x = newX; y = newY; }
    finally { sl.unlockWrite(stamp); }
}
```

**Why it's faster:** In read-heavy workloads where writes are rare, `tryOptimisticRead()` requires just a memory read + `validate()` — no OS interaction, no atomic operation.

**Dangers of StampedLock:**
1. **Not reentrant** — calling `writeLock()` from a thread that already holds it → **deadlock**
2. **Not condition-variable compatible** — no `newCondition()` support
3. **Stamp leaks** — if you forget to unlock with the correct stamp, the lock is corrupted
4. **Complex validation logic** — the optimistic read window must re-read all fields atomically in the validation path

---

## 8. Atomic Classes, CAS, ABA, False Sharing

### Q28. How does Compare-And-Swap (CAS) work at the hardware and Java API level?

**Hardware:** On x86, `CMPXCHG` (compare and exchange) is a single instruction:
```
CMPXCHG [memory], newValue
# If [memory] == EAX (expected), then [memory] = newValue, set ZF=1
# Else EAX = [memory] (load current), clear ZF=0
# With LOCK prefix: atomic across all CPU cores
```

**Java API:**
```java
AtomicInteger ai = new AtomicInteger(5);

// CAS loop — the basis of all lock-free algorithms:
int oldVal, newVal;
do {
    oldVal = ai.get();
    newVal = oldVal + 1;
} while (!ai.compareAndSet(oldVal, newVal));
// If another thread modified ai between get() and compareAndSet(),
// compareAndSet() returns false and we retry

// Same as:
ai.incrementAndGet(); // built-in CAS loop

// Java 9+ VarHandle (more efficient than Unsafe):
VarHandle VH = MethodHandles.lookup().findVarHandle(MyClass.class, "field", int.class);
VH.compareAndSet(obj, expected, newValue);
```

---

### Q29. What is the ABA problem? When does it matter in Java?

```
Thread T1 reads A from address X.
Thread T2: changes X: A → B → A (back to A).
Thread T1: CAS(X, A, C) — SUCCEEDS.
T1 thinks nothing changed, but the object at X has been replaced.
```

**When ABA causes real bugs — lock-free linked list:**
```
Initial:  Head → A → B → C
T1 reads: head = A, next = B (plans to set head = B via CAS)
T2: removes A from list, removes B from list, frees B, re-adds A
List:     Head → A → C
T1: CAS(head, A, B) SUCCEEDS — but B is now freed memory!
Result:   Head → B (freed!) → ??? — heap corruption
```

**Java solutions:**

```java
// AtomicStampedReference — pairs value with an integer version stamp
AtomicStampedReference<Node> head = new AtomicStampedReference<>(initialNode, 0);

int[] stampHolder = new int[1];
Node current = head.get(stampHolder);
int currentStamp = stampHolder[0];

// CAS checks BOTH value AND stamp:
head.compareAndSet(current, newNode, currentStamp, currentStamp + 1);
// T2's intermediate changes would have incremented the stamp
// T1's CAS would fail because stamp doesn't match

// AtomicMarkableReference — stamp replaced with boolean mark
// Use for "mark for deletion" pattern in lock-free lists
```

**ABA in practice:** For most Java application-level code (counters, accumulators), ABA is benign — the "value" at an address changing A→B→A doesn't cause logical errors. ABA matters primarily in **lock-free data structure implementations**.

---

### Q30. Why is `LongAdder` faster than `AtomicLong` under contention? Explain `Striped64`.

```java
// AtomicLong — single memory location, single CAS
AtomicLong counter = new AtomicLong(0);
// Under high contention: threads spin on CAS failures
// 10 threads all trying to increment: 9 fail every round → wasted CPU cycles

// LongAdder — extends Striped64
LongAdder adder = new LongAdder();
adder.increment();
long total = adder.sum(); // NOT a snapshot — other threads may update during sum()
```

**Striped64 internals:**
```
LongAdder
├── long base       ← uncontended case: single CAS on base
└── Cell[] cells    ← contended case: each thread hashes to its own Cell
     ├── Cell[0]:  long value   @Contended  ← padded to full cache line
     ├── Cell[1]:  long value   @Contended
     ├── Cell[2]:  long value   @Contended
     └── Cell[3]:  long value   @Contended

sum() = base + cells[0] + cells[1] + cells[2] + cells[3]
```

**Thread hashing:** Each thread gets a random probe value (thread-local, grows the probe if collision). Low collision → very low contention per Cell.

**`@Contended` — prevents false sharing:**
```java
@jdk.internal.vm.annotation.Contended // pads to fill a 64-byte cache line
static final class Cell {
    volatile long value;
}
// Without padding: cells[0] and cells[1] on the same cache line
// Thread A writes cells[0], Thread B reads cells[1] → cache line invalidated
// False sharing: as bad as a real lock
```

---

## 9. BlockingQueue Variants

### Q31. Compare all BlockingQueue implementations. When does each shine in production?

| Queue | Bounded | Backing | Lock Strategy | Use Case |
|-------|---------|---------|--------------|---------|
| `ArrayBlockingQueue` | Yes | Array | **Single lock** for put + take | Strict capacity control, fair ordering possible |
| `LinkedBlockingQueue` | Optional (default: MAX) | Linked nodes | **Two locks** (put lock + take lock) | Higher throughput: producers and consumers don't block each other |
| `SynchronousQueue` | 0 capacity | None | N/A — direct handoff | `CachedThreadPool`, zero-copy passing between threads |
| `PriorityBlockingQueue` | No | Heap array | Single lock | Task scheduling by priority |
| `DelayQueue` | No | Heap | Single lock | Scheduled retries, TTL cache eviction, rate limiting |
| `LinkedTransferQueue` | No | Linked | Lock-free CAS | Highest throughput producer-consumer, wait for consumer option |

**ArrayBlockingQueue vs LinkedBlockingQueue — the subtle difference:**
```java
// ArrayBlockingQueue: ONE lock for BOTH put and take
// Producer and consumer serialize completely — lower throughput
// BUT: optional fair ordering (FIFO for waiting threads)

// LinkedBlockingQueue: putLock and takeLock are SEPARATE
// Producers and consumers can work concurrently (except when queue is empty/full)
// Higher throughput under concurrent load
// No fairness option
```

---

### Q32. What is `put()` vs `offer()` vs `add()` semantics?

```java
BlockingQueue<String> q = new ArrayBlockingQueue<>(5);

q.add("item");     // throws IllegalStateException if full (non-blocking)
q.offer("item");   // returns false if full (non-blocking)
q.offer("item", 100, MILLISECONDS); // waits up to 100ms, returns false if still full
q.put("item");     // blocks indefinitely if full

q.remove();   // throws NoSuchElementException if empty
q.poll();     // returns null if empty (non-blocking)
q.poll(100, MILLISECONDS); // waits up to 100ms, returns null if still empty
q.take();     // blocks indefinitely if empty
```

**Production rule:** Prefer `offer(timeout)` over `put()` in bounded producers to avoid unbounded blocking. Add timeouts everywhere — a full queue with `put()` can hang the producer thread forever.

---

## 10. CountDownLatch, CyclicBarrier, Semaphore, Phaser, Exchanger

### Q33. Explain `CountDownLatch` vs `CyclicBarrier` with practical examples.

```java
// CountDownLatch — ONE-SHOT, different threads can count and wait
CountDownLatch startSignal = new CountDownLatch(1);  // gun signal
CountDownLatch doneSignal  = new CountDownLatch(10); // 10 workers

// Main thread: wait for all workers
for (int i = 0; i < 10; i++) {
    new Thread(() -> {
        try {
            startSignal.await();  // workers wait for start
            doWork();
        } finally {
            doneSignal.countDown(); // each worker signals completion
        }
    }).start();
}
startSignal.countDown(); // fire the starting gun — releases all workers
doneSignal.await();      // main waits for all workers to finish
// Cannot be reset — create a new one for the next round
```

```java
// CyclicBarrier — REUSABLE, same N threads sync at each phase
CyclicBarrier barrier = new CyclicBarrier(5, () -> {
    // Runs ONCE when all 5 threads arrive — before they proceed
    mergePhaseResults();
});

// Each of 5 simulation threads:
void simulate() {
    for (int phase = 0; phase < 100; phase++) {
        computePhase(phase);
        barrier.await(); // ALL 5 must arrive before ANY proceeds
        // After barrier: barrier resets automatically for next phase
    }
}
```

**CyclicBarrier broken barrier:**
```java
// If one thread throws inside computePhase(), the barrier is broken
// All other threads waiting at barrier.await() get BrokenBarrierException
// The barrier must be reset() before reuse: barrier.reset()
```

---

### Q34. `Semaphore` — implement a connection pool with it.

```java
class ConnectionPool {
    private final Semaphore available;
    private final Connection[] connections;
    private final boolean[] used;

    ConnectionPool(int size) {
        available = new Semaphore(size, true); // fair
        connections = createConnections(size);
        used = new boolean[size];
    }

    Connection acquire() throws InterruptedException {
        available.acquire(); // blocks if all connections in use
        return getAvailableConnection();
    }

    void release(Connection c) {
        returnConnection(c);
        available.release(); // signal one waiting thread
    }
}

// Rate limiter variant:
Semaphore rateLimiter = new Semaphore(100); // 100 concurrent requests max

void handleRequest() {
    if (!rateLimiter.tryAcquire(500, MILLISECONDS)) {
        throw new TooManyRequestsException();
    }
    try { processRequest(); }
    finally { rateLimiter.release(); }
}
```

---

### Q35. When does `Phaser` supersede `CountDownLatch` and `CyclicBarrier`?

```java
// Phaser advantages:
// 1. Dynamic registration — parties can join/leave at runtime
// 2. Multiple phases without creating new objects
// 3. Tiered phasers for large-scale parallel algorithms

Phaser phaser = new Phaser(1); // "1" for the main thread

// Workers register dynamically:
for (int i = 0; i < workers; i++) {
    phaser.register(); // add a party
    new Thread(() -> {
        // Phase 1 work
        phaser.arriveAndAwaitAdvance(); // sync at phase 1
        // Phase 2 work
        phaser.arriveAndAwaitAdvance(); // sync at phase 2
        phaser.arriveAndDeregister();   // leave — no longer participating
    }).start();
}

phaser.arriveAndAwaitAdvance(); // main: sync at phase 1
phaser.arriveAndAwaitAdvance(); // main: sync at phase 2
phaser.arriveAndDeregister();   // main deregisters

// Termination: phaser.isTerminated() — true when all parties deregister
```

---

### Q36. What is `Exchanger`? Give a realistic production scenario.

```java
// Exchanger: exactly 2 threads meet at a synchronization point and swap data

Exchanger<List<String>> exchanger = new Exchanger<>();

// THREAD 1 — Data Filler:
void fillBuffer() throws InterruptedException {
    List<String> buffer = new ArrayList<>();
    while (running) {
        buffer.clear();
        for (int i = 0; i < BATCH_SIZE; i++) {
            buffer.add(fetchNextRecord());
        }
        buffer = exchanger.exchange(buffer); // hand full buffer, get empty one
    }
}

// THREAD 2 — Data Processor:
void processBuffer() throws InterruptedException {
    List<String> buffer = new ArrayList<>(); // starts with empty buffer
    while (running) {
        buffer = exchanger.exchange(buffer); // give empty, receive full
        for (String record : buffer) {
            processRecord(record);
        }
    }
}
// Double-buffering: filler and processor work simultaneously with no shared state
```

---

## 11. CompletableFuture — Deep Dive

### Q37. `thenApply()` vs `thenCompose()` — explain with async chain examples.

```java
// thenApply — map: T → U (synchronous function inside async)
CompletableFuture<String> userId = getUserIdAsync(); // CF<String>
CompletableFuture<String> upper  = userId.thenApply(String::toUpperCase); // CF<String>

// thenCompose — flatMap: T → CompletableFuture<U>
CompletableFuture<String> userId = getUserIdAsync(); // CF<String>
CompletableFuture<User> user = userId.thenCompose(id -> getUserAsync(id)); // CF<User>
// NOT: thenApply(id -> getUserAsync(id)) — that gives CF<CF<User>> ← WRONG

// Complete async chain:
CompletableFuture<Response> result =
    getUserIdAsync()
        .thenCompose(this::fetchUserDetails)      // async: userId → CF<User>
        .thenCompose(user -> fetchOrders(user.id)) // async: User → CF<List<Order>>
        .thenApply(orders -> buildResponse(orders)) // sync: List<Order> → Response
        .exceptionally(ex -> Response.error(ex.getMessage()));
```

---

### Q38. Exception handling — `exceptionally()` vs `handle()` vs `whenComplete()`.

```java
CompletableFuture<String> future = callExternalService();

// exceptionally — only on failure, can return recovery value or re-throw
future.exceptionally(ex -> {
    if (ex instanceof TimeoutException) return "default-value";
    throw new RuntimeException(ex); // re-throw — propagates downstream
});

// handle — BOTH success and failure, can transform either
future.handle((result, ex) -> {
    if (ex != null) return "error: " + ex.getMessage();
    return result.toUpperCase();
    // return type must match the next stage
});

// whenComplete — BOTH paths, CANNOT change the result
future.whenComplete((result, ex) -> {
    log.info("Completed: result={}, ex={}", result, ex);
    // return value is ignored — same future propagates
});

// Practical exception pipeline:
CompletableFuture.supplyAsync(() -> callService())
    .thenApply(r -> transform(r))
    .exceptionally(ex -> {
        metrics.increment("failures");
        return fallbackValue(); // graceful degradation
    })
    .whenComplete((r, ex) -> {
        audit.log(r, ex); // always log, regardless of outcome
    });
```

---

### Q39. On which thread does a `CompletableFuture` callback execute? Why does this matter?

```java
// Without Async suffix — callback runs on the completing thread:
CompletableFuture<String> cf = CompletableFuture.supplyAsync(() -> fetchData());
// supplyAsync: runs in ForkJoinPool.commonPool()
// thenApply: runs in SAME thread that completed cf (commonPool worker)

cf.thenApply(data -> process(data)); // runs in ForkJoinPool worker

// If cf was already complete when thenApply was called:
// The callback runs in the CALLING thread (main thread or whoever called thenApply)

// This causes context bugs in production:
// - MDC (log correlation IDs) bound to calling thread not present in callback thread
// - SecurityContext (Spring Security) not propagated
// - Hibernate session not available

// Fix — always specify an executor:
cf.thenApplyAsync(data -> process(data), myExecutor); // runs in myExecutor

// Production pattern with MDC propagation:
Map<String, String> mdcContext = MDC.getCopyOfContextMap();
cf.thenApplyAsync(data -> {
    MDC.setContextMap(mdcContext); // restore MDC in callback thread
    try { return process(data); }
    finally { MDC.clear(); }
}, myExecutor);
```

---

### Q40. `allOf()` vs `anyOf()` — what are the result extraction gotchas?

```java
// allOf — completes when ALL complete, returns CompletableFuture<Void>
CompletableFuture<User> userFuture  = fetchUserAsync(id);
CompletableFuture<Order> orderFuture = fetchOrderAsync(id);
CompletableFuture<Void> allFutures  = CompletableFuture.allOf(userFuture, orderFuture);

// GOTCHA: allOf result is Void — you must call join() on originals to get results
allFutures.thenApply(v -> {
    User user   = userFuture.join();   // safe: already complete when allOf fires
    Order order = orderFuture.join();
    return new Dashboard(user, order);
});

// allOf exception behavior:
// If ONE sub-future fails → allOf fails immediately
// Other sub-futures CONTINUE running (no cancellation)
// Their exceptions are NOT in allOf's exception — must check individually

// anyOf — completes when the FIRST completes, returns CompletableFuture<Object>
CompletableFuture<Object> first = CompletableFuture.anyOf(f1, f2, f3);
// GOTCHA: return type is Object — you must cast
// GOTCHA: losing sub-futures keep running in background — no automatic cleanup

// Safe pattern for "fastest wins":
CompletableFuture<String> result = CompletableFuture.anyOf(
    callServiceA().thenApply(r -> "A:" + r),
    callServiceB().thenApply(r -> "B:" + r)
).thenApply(Object::toString);
```

---

### Q41. What is the ForkJoinPool common pool danger with `CompletableFuture`?

```java
// CompletableFuture.supplyAsync() without executor → ForkJoinPool.commonPool()
// Parallel streams → same ForkJoinPool.commonPool()

// Deadlock scenario — ALL common pool threads block waiting for each other:
CompletableFuture<Integer> outer = CompletableFuture.supplyAsync(() -> {
    // This submits work to the SAME common pool this thread is in:
    CompletableFuture<Integer> inner = CompletableFuture.supplyAsync(() -> 42);
    return inner.join(); // blocks a common pool thread waiting for a common pool task
    // If common pool is fully occupied → deadlock (no thread to run inner)
});

// Production rule: ALWAYS provide an explicit executor for production async chains:
private static final ExecutorService asyncPool =
    Executors.newFixedThreadPool(50, new ThreadFactoryBuilder()
        .setNameFormat("async-pool-%d")
        .setDaemon(true)
        .build());

CompletableFuture.supplyAsync(() -> fetchData(), asyncPool)
    .thenApplyAsync(data -> process(data), asyncPool);
```

---

## 12. Fork/Join Framework

### Q42. Explain work-stealing in `ForkJoinPool`. Why is it cache-friendly?

```
Worker 0 deque:  [task1, task2, task3, task4]  ← own head (LIFO)
Worker 1 deque:  [task5, task6]
Worker 2 deque:  [] (idle)

Worker 2 STEALS from Worker 0's TAIL (FIFO — takes task4, the oldest)

Why this is cache-friendly:
- Worker 0 accesses task1 (newest) from head — likely in cache
- Worker 2 steals task4 (oldest) from tail — likely not in cache anyway
- Minimal cache contention between stealer and owner
- Stolen tasks tend to be coarser-grained (parent tasks) — fewer steals needed
```

```java
// RecursiveTask — returns a value
class MergeSort extends RecursiveTask<int[]> {
    private final int[] array;
    private static final int THRESHOLD = 1000;

    @Override
    protected int[] compute() {
        if (array.length <= THRESHOLD) {
            return sortSequentially(array); // base case
        }
        int mid = array.length / 2;
        MergeSort left  = new MergeSort(Arrays.copyOfRange(array, 0, mid));
        MergeSort right = new MergeSort(Arrays.copyOfRange(array, mid, array.length));

        left.fork();           // push left onto current thread's deque
        int[] rightResult = right.compute(); // compute right in CURRENT thread
        int[] leftResult  = left.join();     // retrieve left (may steal if not done)

        return merge(leftResult, rightResult);
    }
}

ForkJoinPool pool = new ForkJoinPool(Runtime.getRuntime().availableProcessors());
int[] sorted = pool.invoke(new MergeSort(largeArray));
```

**`fork()` then `compute()` then `join()` — not `fork()` both:** The current thread should compute one subtask directly rather than forking both. Forking both and joining both wastes a thread context switch.

---

### Q43. When does `ForkJoinPool` cause thread starvation deadlock?

```java
// Anti-pattern: blocking in ForkJoinPool tasks
ForkJoinPool pool = ForkJoinPool.commonPool(); // e.g., 8 threads on 8-core machine

pool.submit(() -> {
    CompletableFuture<String> cf = CompletableFuture.supplyAsync(() -> fetch()); // also goes to commonPool
    String result = cf.join(); // BLOCKS this ForkJoinPool thread waiting for a commonPool thread
    // If all 8 threads are doing this → deadlock: all waiting for tasks that can't run
});

// Fix: use ManagedBlocker to tell ForkJoinPool to add a spare thread:
ForkJoinPool.managedBlock(new ForkJoinPool.ManagedBlocker() {
    public boolean block() throws InterruptedException {
        result = cf.join(); return true;
    }
    public boolean isReleasable() { return cf.isDone(); }
});
// OR: use a separate non-ForkJoinPool executor for blocking calls
```

---

## 13. ThreadLocal — Patterns & Memory Leaks

### Q44. What are legitimate `ThreadLocal` use cases?

```java
// 1. Non-thread-safe formatters (SimpleDateFormat, NumberFormat):
static final ThreadLocal<DateFormat> DATE_FORMAT =
    ThreadLocal.withInitial(() -> new SimpleDateFormat("yyyy-MM-dd"));
// Each thread gets its own instance — no synchronization needed

// 2. Request context in web servers (Servlet, Spring MVC):
static final ThreadLocal<RequestContext> REQUEST_CTX = new ThreadLocal<>();
// Filter sets it; downstream code reads it; filter removes it in finally

// 3. Database transaction context:
// Spring's TransactionSynchronizationManager stores the current Connection/Session
// in a ThreadLocal — binds the transaction to the current thread

// 4. Avoiding deep parameter passing:
// Instead of passing a "context" object 15 levels deep:
AUDIT_CONTEXT.set(new AuditContext(userId, requestId));
// … 15 method calls later:
AUDIT_CONTEXT.get().recordChange(entity);
AUDIT_CONTEXT.remove(); // CRITICAL
```

---

### Q45. How does `ThreadLocal` cause memory leaks in thread pools? Prove it.

```java
// Thread pool threads live for the application's lifetime.
// ThreadLocalMap is stored on the Thread object itself.
// If you set a ThreadLocal and never remove it:

static final ThreadLocal<byte[]> largeData = new ThreadLocal<>();

// Task 1 executed by Thread-0:
largeData.set(new byte[50 * 1024 * 1024]); // 50MB
// process...
// FORGOT: largeData.remove()

// Task 2 executed by same Thread-0 (thread pool reuses Thread-0):
// largeData.get() still returns the 50MB byte[] from Task 1
// Even if Task 2 never touches it, the 50MB is retained on Thread-0

// With 50 threads in pool and one forgotten 50MB ThreadLocal per thread:
// 50 × 50MB = 2.5GB permanent heap bloat
```

**ThreadLocalMap's WeakKey behavior (a subtle truth):**
```
ThreadLocalMap entry: WeakReference(ThreadLocal key) → Strong ref(value)
- If the ThreadLocal variable itself is GC'd (no more strong refs to the key):
  the key is collected, entry becomes (null key, live value)
- These orphaned entries are cleaned up lazily — not immediately
- If the ThreadLocal static field exists (common case), the key is NEVER GC'd
  → entries are never cleaned up → true memory leak
```

**Fix — always remove in a try-finally:**
```java
try {
    largeData.set(computeData());
    doWork();
} finally {
    largeData.remove(); // guaranteed cleanup even if doWork throws
}
```

---

## 14. Virtual Threads (Java 21+) & Structured Concurrency

### Q46. What are virtual threads? Platform thread vs virtual thread internals.

```
Platform Thread (Java 1–20):
  JVM Thread ─── 1:1 ─── OS Thread ─── CPU Core
  ~1MB stack (OS-allocated)
  OS context switch (~1-10 microseconds)
  JVM process can have ~thousands (OS limit)

Virtual Thread (Java 21+):
  VirtualThread ─── M:N ─── CarrierThread (platform) ─── CPU Core
  ~1KB initial stack (heap-allocated, grows as needed)
  JVM context switch (~nanoseconds)
  JVM process can have millions
```

```java
// Creating virtual threads:
Thread vt = Thread.ofVirtual().name("vt-1").start(() -> handleRequest());

// Executor for virtual threads:
ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor();
// Creates one virtual thread per task — 1 million tasks = 1 million virtual threads
// Memory: ~1KB × 1M = 1GB (vs 1MB × 1M = 1TB for platform threads)

// Blocking I/O on virtual threads:
// Before (platform threads): blocking read() blocks the OS thread
// After (virtual threads): blocking read() UNMOUNTS the virtual thread from carrier
// Carrier thread is freed to run other virtual threads
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    for (int i = 0; i < 100_000; i++) {
        executor.submit(() -> {
            // This blocks — but only unmounts the virtual thread, not the carrier
            String response = httpClient.get("https://api.example.com");
            process(response);
        });
    }
}
// All 100,000 requests run concurrently with only #CPU carrier threads
```

---

### Q47. What is virtual thread pinning? Full production impact analysis.

**Pinning** = virtual thread cannot unmount from its carrier thread.

```java
// PINNING SCENARIO 1 — synchronized block (Java 21, 22, 23):
synchronized (lock) {
    String response = httpClient.get(url); // blocks here
    // virtual thread CANNOT unmount — carrier thread is blocked too
    // if 8 carrier threads all pinned on I/O: entire pool stalls
}
// FIX: replace synchronized with ReentrantLock
ReentrantLock lock = new ReentrantLock();
lock.lock();
try {
    String response = httpClient.get(url); // can unmount here
} finally { lock.unlock(); }

// PINNING SCENARIO 2 — native methods (JNI):
// Cannot avoid — virtual thread is pinned for the duration of native call

// DIAGNOSIS:
// JVM flag:
-Djdk.tracePinnedThreads=full   // logs stack trace every time pinning occurs
-Djdk.tracePinnedThreads=short  // just the blocking frame

// JFR event: jdk.VirtualThreadPinned — captured automatically
```

**Java 24 fix (JEP 491):** `synchronized` no longer pins virtual threads in most cases. The JVM restructured how intrinsic locks interact with virtual thread mounting/unmounting. This removes the primary migration obstacle.

---

### Q48. What is Structured Concurrency? How does it improve on `CompletableFuture`?

```java
// Traditional CompletableFuture — no automatic cleanup:
CompletableFuture<User> userFuture  = fetchUserAsync(id);
CompletableFuture<Order> orderFuture = fetchOrderAsync(id);
// If userFuture fails, orderFuture keeps running in background
// No automatic cancellation, potential thread leak

// Structured Concurrency (Java 21+ preview, JEP 428/453):
try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
    Subtask<User>  user  = scope.fork(() -> fetchUser(id));
    Subtask<Order> order = scope.fork(() -> fetchOrder(id));

    scope.join();           // wait for ALL subtasks
    scope.throwIfFailed();  // if any failed, re-throw the first exception
                            // AND cancel all other running subtasks

    return new Response(user.get(), order.get());
} // scope.close() cancels any still-running subtasks — guaranteed

// ShutdownOnSuccess — race/speculative execution:
try (var scope = new StructuredTaskScope.ShutdownOnSuccess<String>()) {
    scope.fork(() -> callServiceA()); // try A and B simultaneously
    scope.fork(() -> callServiceB());
    scope.join(); // wait for first success
    return scope.result(); // returns first successful result, cancels the other
}
```

**Structured vs CompletableFuture:**

| Aspect | CompletableFuture | StructuredTaskScope |
|--------|------------------|---------------------|
| Cancellation on failure | Manual | Automatic |
| Thread leak risk | High | None (scope ensures cleanup) |
| Error propagation | Complex chain | `throwIfFailed()` |
| Observability | Hard (threads unnamed) | All subtasks named, traceable |
| Code readability | Callback chain | Sequential-looking code |

---

### Q49. What is `ScopedValue`? Why does it replace `ThreadLocal` for virtual threads?

```java
// ScopedValue (Java 21+ preview — JEP 446):
static final ScopedValue<RequestContext> CTX = ScopedValue.newInstance();

// Bind in request handler:
ScopedValue.where(CTX, new RequestContext(userId, requestId))
    .run(() -> {
        // CTX.get() works anywhere within this call tree
        processRequest();
        // child virtual threads forked here automatically inherit CTX
    });
// After run() exits: binding is automatically removed — no remove() needed

// Reading in deeply nested code:
void deeplyNestedMethod() {
    RequestContext ctx = CTX.get(); // always available within the scope
}
```

**ThreadLocal vs ScopedValue comparison:**

| Aspect | ThreadLocal | ScopedValue |
|--------|------------|-------------|
| Mutability | Mutable (`set()` anywhere) | Immutable within scope (rebind = new scope) |
| Cleanup | Manual `remove()` | Automatic at scope exit |
| Memory with VT | Millions of entries at scale | Stack-based, cleaned with call frame |
| Inheritance | Manual with InheritableThreadLocal | Automatic in child threads/virtual threads |
| Safety | Can be accidentally overwritten | Read-only in child scopes |
| Performance | Hash lookup | Stack-based lookup — faster |

---

## 15. Practical Coding Scenarios

### Q50. Implement a thread-safe bounded blocking queue from scratch (asked at Google, Amazon, Uber).

```java
class BoundedBlockingQueue<T> {
    private final Queue<T> queue = new LinkedList<>();
    private final int capacity;
    private final ReentrantLock lock = new ReentrantLock();
    private final Condition notFull  = lock.newCondition(); // producers wait here
    private final Condition notEmpty = lock.newCondition(); // consumers wait here

    public BoundedBlockingQueue(int capacity) {
        this.capacity = capacity;
    }

    public void put(T item) throws InterruptedException {
        lock.lock();
        try {
            while (queue.size() == capacity) { // WHILE not IF — spurious wakeup
                notFull.await();               // releases lock, waits
            }
            queue.offer(item);
            notEmpty.signal(); // signal ONE consumer (not all — efficient)
        } finally {
            lock.unlock(); // ALWAYS in finally
        }
    }

    public T take() throws InterruptedException {
        lock.lock();
        try {
            while (queue.isEmpty()) {
                notEmpty.await();
            }
            T item = queue.poll();
            notFull.signal(); // signal ONE producer
            return item;
        } finally {
            lock.unlock();
        }
    }

    public T poll(long timeout, TimeUnit unit) throws InterruptedException {
        lock.lock();
        try {
            long nanos = unit.toNanos(timeout);
            while (queue.isEmpty()) {
                if (nanos <= 0) return null; // timed out
                nanos = notEmpty.awaitNanos(nanos); // returns remaining nanos
            }
            T item = queue.poll();
            notFull.signal();
            return item;
        } finally {
            lock.unlock();
        }
    }

    public int size() {
        lock.lock();
        try { return queue.size(); }
        finally { lock.unlock(); }
    }
}
```

**Key insight interviewers look for:**
1. Two `Condition` objects (not one) — `signal()` only the right waiters
2. `while` loop around `await()` — spurious wakeup defense
3. `finally` for `unlock()` — always
4. `signal()` not `signalAll()` — no thundering herd

---

### Q51. Implement a Token Bucket rate limiter using concurrency primitives (asked at Uber, Razorpay).

```java
class TokenBucketRateLimiter {
    private final long capacity;         // max tokens (burst capacity)
    private final double refillRatePerNs; // tokens per nanosecond
    private double tokens;
    private long lastRefillNanos;
    private final ReentrantLock lock = new ReentrantLock();

    public TokenBucketRateLimiter(long capacity, long tokensPerSecond) {
        this.capacity = capacity;
        this.refillRatePerNs = (double) tokensPerSecond / 1_000_000_000L;
        this.tokens = capacity; // start full
        this.lastRefillNanos = System.nanoTime();
    }

    public boolean tryAcquire() {
        return tryAcquire(1);
    }

    public boolean tryAcquire(int permits) {
        lock.lock();
        try {
            refill();
            if (tokens >= permits) {
                tokens -= permits;
                return true;
            }
            return false;
        } finally {
            lock.unlock();
        }
    }

    // Blocking acquire — wait until tokens are available
    public void acquire() throws InterruptedException {
        lock.lock();
        try {
            while (true) {
                refill();
                if (tokens >= 1) {
                    tokens--;
                    return;
                }
                // Calculate wait time until next token available
                double deficit = 1.0 - tokens;
                long waitNs = (long) (deficit / refillRatePerNs);
                // Use Condition.awaitNanos for interruptible wait
                Thread.sleep(waitNs / 1_000_000, (int)(waitNs % 1_000_000));
            }
        } finally {
            lock.unlock();
        }
    }

    private void refill() {
        long now = System.nanoTime();
        double elapsed = now - lastRefillNanos;
        tokens = Math.min(capacity, tokens + elapsed * refillRatePerNs);
        lastRefillNanos = now;
    }
}

// Per-user rate limiting with ConcurrentHashMap:
class PerUserRateLimiter {
    private final ConcurrentHashMap<String, TokenBucketRateLimiter> limiters = new ConcurrentHashMap<>();
    private final long capacity;
    private final long ratePerSecond;

    public boolean tryAcquire(String userId) {
        TokenBucketRateLimiter limiter = limiters.computeIfAbsent(
            userId,
            k -> new TokenBucketRateLimiter(capacity, ratePerSecond)
        ); // computeIfAbsent is atomic — only one limiter created per user
        return limiter.tryAcquire();
    }
}
```

---

### Q52. Implement a thread-safe LRU cache with TTL and compute-on-miss (asked at Amazon, Flipkart).

```java
class ConcurrentLRUCache<K, V> {
    private final int maxSize;
    private final long ttlNanos;
    private final Function<K, V> loader;
    private final ReadWriteLock rwLock = new ReentrantReadWriteLock();

    // LinkedHashMap in access-order mode — LRU eviction
    private final Map<K, CacheEntry<V>> cache;

    // Tracks in-flight computations to prevent thundering herd
    private final ConcurrentHashMap<K, CompletableFuture<V>> inflight = new ConcurrentHashMap<>();

    public ConcurrentLRUCache(int maxSize, Duration ttl, Function<K, V> loader) {
        this.maxSize  = maxSize;
        this.ttlNanos = ttl.toNanos();
        this.loader   = loader;
        this.cache    = new LinkedHashMap<>(maxSize, 0.75f, true) {
            @Override
            protected boolean removeEldestEntry(Map.Entry<K, CacheEntry<V>> eldest) {
                return size() > maxSize;
            }
        };
    }

    public V get(K key) throws Exception {
        // Fast path — read lock
        rwLock.readLock().lock();
        try {
            CacheEntry<V> entry = cache.get(key);
            if (entry != null && !entry.isExpired()) return entry.value;
        } finally { rwLock.readLock().unlock(); }

        // Cache miss — prevent thundering herd with computeIfAbsent
        CompletableFuture<V> future = inflight.computeIfAbsent(key, k ->
            CompletableFuture.supplyAsync(() -> loader.apply(k))
                .whenComplete((v, ex) -> {
                    if (ex == null) {
                        rwLock.writeLock().lock();
                        try { cache.put(k, new CacheEntry<>(v, ttlNanos)); }
                        finally { rwLock.writeLock().unlock(); }
                    }
                    inflight.remove(k); // cleanup inflight marker
                })
        );
        return future.get(); // wait for compute to finish (other threads reuse this future)
    }

    private static class CacheEntry<V> {
        final V value;
        final long expiryNanos;
        CacheEntry(V v, long ttlNanos) {
            this.value = v;
            this.expiryNanos = System.nanoTime() + ttlNanos;
        }
        boolean isExpired() { return System.nanoTime() > expiryNanos; }
    }
}
```

---

### Q53. Implement `Semaphore` from scratch using `ReentrantLock` + `Condition`.

```java
class Semaphore {
    private int permits;
    private final ReentrantLock lock = new ReentrantLock(true); // fair
    private final Condition available = lock.newCondition();

    public Semaphore(int permits) { this.permits = permits; }

    public void acquire() throws InterruptedException {
        lock.lock();
        try {
            while (permits == 0) available.await();
            permits--;
        } finally { lock.unlock(); }
    }

    public boolean tryAcquire(long timeout, TimeUnit unit) throws InterruptedException {
        lock.lock();
        try {
            long nanos = unit.toNanos(timeout);
            while (permits == 0) {
                if (nanos <= 0) return false;
                nanos = available.awaitNanos(nanos);
            }
            permits--;
            return true;
        } finally { lock.unlock(); }
    }

    public void release() {
        lock.lock();
        try {
            permits++;
            available.signal(); // signal ONE waiter
        } finally { lock.unlock(); }
    }
}
```

---

## 16. Production Debugging & Observability

### Q54. How do you take and analyze a thread dump to diagnose a production issue?

```bash
# Take thread dump (multiple methods):
jstack <pid>                     # prints to stdout
jcmd <pid> Thread.print          # preferred in JDK 11+
kill -3 <pid>                    # sends SIGQUIT, JVM prints to stdout

# For stuck threads (take 3 dumps 5s apart to distinguish stalled vs just slow):
for i in 1 2 3; do jstack <pid> > /tmp/td-$i.txt; sleep 5; done

# Key thread dump patterns to look for:

# 1. Deadlock:
# "Found one Java-level deadlock:"
# Thread-1 waiting to lock 0x00000007b72d9850 held by Thread-2
# Thread-2 waiting to lock 0x00000007b72d9810 held by Thread-1

# 2. Thread pool saturation (all threads BLOCKED on same resource):
# "pool-1-thread-1" BLOCKED on lock 0x...
# "pool-1-thread-2" BLOCKED on lock 0x...
# ... (all N threads BLOCKED — pool is deadlocked on one resource)

# 3. High RUNNABLE threads (check CPU):
# Many threads in RUNNABLE but CPU near 100% → hot spin loop or CAS storm

# 4. Thread waiting in I/O (correct virtual thread behavior):
# "VirtualThread[#100,...]" WAITING on java.lang.VirtualThread.parkNanos
```

---

### Q55. How do you use JFR to diagnose concurrency issues?

```bash
# Start recording:
jcmd <pid> JFR.start settings=default name=conc duration=60s filename=/tmp/conc.jfr

# Key JFR events for concurrency:
# jdk.ThreadSleep              — every Thread.sleep() call with duration
# jdk.JavaMonitorWait          — wait() calls on object monitors
# jdk.JavaMonitorEnter         — synchronized block entry (lock acquisition)
# jdk.JavaMonitorInflate       — lock promotion to heavyweight monitor
# jdk.ThreadPark               — LockSupport.park() (used by ReentrantLock, etc.)
# jdk.VirtualThreadPinned      — virtual thread pinning events
# jdk.VirtualThreadSubmitFailed — failed to submit virtual thread task
# jdk.ExecutionSample          — CPU profiling (RUNNABLE thread samples)

# In JDK Mission Control (JMC):
# Thread tab → shows each thread's activity timeline
# Lock Instances tab → shows which locks have highest contention
# Hot Methods tab → where CPU time is spent
```

**Programmatic JFR recording:**
```java
Configuration config = Configuration.getConfiguration("default");
try (Recording recording = new Recording(config)) {
    recording.enable("jdk.JavaMonitorEnter").withThreshold(Duration.ofMillis(10));
    recording.enable("jdk.VirtualThreadPinned");
    recording.start();
    // ... run workload ...
    recording.dump(Path.of("/tmp/recording.jfr"));
}
```

---

## 17. Rapid-Fire Gotchas

### Q56. What is the output? (Volatile reference — does it protect the object's fields?)

```java
class Data { int x; int y; }
volatile Data data = new Data();

// Thread 1:
data.x = 42; // NOT protected by volatile — only the reference is volatile
data.y = 99;

// Thread 2:
Data d = data; // volatile read — sees the Data reference
System.out.println(d.x); // may print 0 — data.x is NOT volatile
```

`volatile` on a reference protects the **reference itself** (the pointer), not the object's fields. To safely share mutable object state, each field must be individually `volatile`, or the object must be safely published via `synchronized`.

---

### Q57. Can two threads call different `synchronized` methods on the same object concurrently?

**No.** All `synchronized` instance methods use the SAME monitor (`this`). Thread A in `synchronized void foo()` holds the monitor — Thread B trying to enter `synchronized void bar()` on the same object is BLOCKED.

**Exception:** Non-synchronized methods are always concurrent. Static synchronized methods use a different monitor (`ClassName.class`).

---

### Q58. What happens when an uncaught exception is thrown in a thread pool worker?

```java
ExecutorService pool = Executors.newFixedThreadPool(5);
pool.execute(() -> {
    throw new RuntimeException("Silent failure");
    // Exception → UncaughtExceptionHandler → default: prints to stderr
    // The throwing thread is TERMINATED
    // ThreadPoolExecutor creates a REPLACEMENT thread immediately
    // The exception is silently swallowed from the caller's perspective
});

// With submit() — exception stored in Future:
Future<?> f = pool.submit(() -> { throw new RuntimeException("Captured"); });
f.get(); // throws ExecutionException wrapping the RuntimeException
```

---

### Q59. What is `sleep(0)` vs `yield()` vs no-op?

```java
Thread.sleep(0);  // Triggers OS scheduler — may allow lower-priority threads to run
                  // The current thread immediately becomes eligible for rescheduling

Thread.yield();   // Hints to scheduler: other threads of SAME or HIGHER priority may run
                  // No guarantee — scheduler may ignore it entirely
                  // Thread state stays RUNNABLE

// In practice:
// sleep(0) on Linux → calls sched_yield() — similar to yield()
// Both are rarely useful in production code (they're workarounds for busy-wait patterns)
// Prefer a proper synchronization mechanism instead
```

---

### Q60. What is `computeIfAbsent()` on `ConcurrentHashMap` — is it truly atomic?

```java
ConcurrentHashMap<String, List<String>> map = new ConcurrentHashMap<>();

// computeIfAbsent — atomic: only ONE thread computes the value for a key
List<String> list = map.computeIfAbsent("key", k -> new ArrayList<>());
// If two threads race: only one runs the lambda; the other waits and gets the same result

// GOTCHA: computeIfAbsent does NOT hold the lock during the entire computation
// The "bin lock" is held, but only for the lookup and put steps
// The lambda executes WITHOUT the lock in Java 8 early versions (fixed in Java 9+)

// GOTCHA 2: Recursive use deadlocks in some JVM versions:
// Do NOT call computeIfAbsent inside a computeIfAbsent lambda on the same map key
map.computeIfAbsent("key", k -> {
    map.computeIfAbsent("key", k2 -> new ArrayList<>()); // potential deadlock
    return new ArrayList<>();
});
```

---

### Q61. What is the "happens-before" for static initializers?

```java
class LazyInit {
    private static final ExpensiveObject obj;
    static {
        obj = new ExpensiveObject(); // static initializer
        // The JVM guarantees:
        // This initializer completes BEFORE any thread can use LazyInit.obj
        // No additional synchronization needed for safely published static finals
    }
    static ExpensiveObject getInstance() { return obj; }
}

// This is why the static holder pattern for singletons is safe:
// The class loader guarantees Holder's static initializer runs exactly once,
// and its completion happens-before any thread sees Holder.INSTANCE
```

---

### Q62. Why is `Collections.synchronizedList()` still not thread-safe for iteration?

```java
List<String> syncList = Collections.synchronizedList(new ArrayList<>());
syncList.add("a");
syncList.add("b");

// UNSAFE — the iterator itself is not synchronized:
for (String s : syncList) { // ConcurrentModificationException possible
    process(s);
}

// SAFE — manually synchronize on the list:
synchronized (syncList) {
    for (String s : syncList) { // holds syncList's intrinsic lock
        process(s);
    }
}

// Better: use CopyOnWriteArrayList for read-heavy concurrent iteration:
List<String> cowList = new CopyOnWriteArrayList<>();
// iteration is always safe (snapshot) — no synchronization needed
// writes create a new copy — expensive for write-heavy workloads
```

---

## Quick Reference — Production Concurrency Cheat Sheet

```
LOCK SELECTION:
  Simple mutual exclusion           → synchronized
  Need tryLock/timeout/fairness     → ReentrantLock
  Read-heavy, write-rare            → ReadWriteLock or StampedLock
  Ultra-high read throughput        → StampedLock (optimistic read)
  Counter under high contention     → LongAdder (not AtomicLong)

EXECUTOR SELECTION:
  CPU-bound parallel tasks          → ForkJoinPool (parallel streams)
  I/O-bound tasks, many concurrent  → Virtual thread executor (Java 21+)
  Fixed bounded concurrency         → ThreadPoolExecutor (tuned)
  Scheduled / periodic tasks        → ScheduledThreadPoolExecutor
  Never use                         → newCachedThreadPool() in production

SYNCHRONIZER SELECTION:
  One-shot start/done signal        → CountDownLatch
  Iterative phase barrier           → CyclicBarrier
  Resource pool / rate limit        → Semaphore
  Dynamic multi-phase               → Phaser
  Two-thread data swap              → Exchanger

COLLECTION SELECTION:
  Concurrent map                    → ConcurrentHashMap (never synchronizedMap)
  Read-heavy list                   → CopyOnWriteArrayList
  Producer-consumer bounded         → ArrayBlockingQueue
  Producer-consumer high throughput → LinkedBlockingQueue
  Direct handoff                    → SynchronousQueue

MODERN JAVA (21+):
  High concurrency I/O              → Virtual threads (VirtualThread)
  Context propagation               → ScopedValue (not ThreadLocal)
  Parallel subtasks with cleanup    → StructuredTaskScope

COMMON PRODUCTION BUGS:
  if(condition) wait() → use while()
  execute() vs submit() → always submit() for error visibility
  new CachedThreadPool() → bounds threads with maxPoolSize
  synchronized + blocking I/O → use ReentrantLock (pre-Java-24)
  ThreadLocal without remove() → always try-finally remove()
  CompletableFuture without executor → always specify explicit executor
  allOf() result extraction → must call join() on individual futures
```
