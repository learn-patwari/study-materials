# Core Java — Experienced Interview Q&A (10–15 Years)
> Excludes: Threads/Concurrency | Streams/Functional — those are separate files.
> Sourced from real interviews at Google, Amazon, JP Morgan, Goldman Sachs, Flipkart, Uber, PayPal, Morgan Stanley.

---

## Table of Contents

1. [OOP Internals & Design](#1-oop-internals--design)
2. [Java Collections Internals](#2-java-collections-internals)
3. [Generics, Type Erasure & Wildcards](#3-generics-type-erasure--wildcards)
4. [Exception Handling — Edge Cases](#4-exception-handling--edge-cases)
5. [String Internals & String Pool](#5-string-internals--string-pool)
6. [Java Memory Model (JMM)](#6-java-memory-model-jmm)
7. [Reflection & Annotations](#7-reflection--annotations)
8. [Modern Java Features (Java 8–25)](#8-modern-java-features-java-825)
9. [Serialization — Deep Edge Cases](#9-serialization--deep-edge-cases)
10. [equals() / hashCode() Contract](#10-equals--hashcode-contract)
11. [Inner Classes, Lambdas & Functional Interfaces](#11-inner-classes-lambdas--functional-interfaces)
12. [Autoboxing & Integer Cache Pitfalls](#12-autoboxing--integer-cache-pitfalls)
13. [Enums — Internals & Patterns](#13-enums--internals--patterns)
14. [Interface Evolution (Java 8–25)](#14-interface-evolution-java-825)
15. [Comparable vs Comparator — Deep](#15-comparable-vs-comparator--deep)
16. [Classic Gotchas & Output Prediction](#16-classic-gotchas--output-prediction)

---

## 1. OOP Internals & Design

### Q1. What is the difference between method overriding and method hiding? How does the JVM resolve each?

**Method Overriding** (instance methods): Resolved at **runtime** via dynamic dispatch (vtable lookup). The actual type of the object determines which method runs.

**Method Hiding** (static methods): Resolved at **compile time** based on the **reference type**. The subclass's static method does not override — it hides the parent's.

```java
class Parent {
    static void staticMethod() { System.out.println("Parent static"); }
    void instanceMethod()      { System.out.println("Parent instance"); }
}
class Child extends Parent {
    static void staticMethod() { System.out.println("Child static"); }   // hides
    @Override
    void instanceMethod()      { System.out.println("Child instance"); }  // overrides
}

Parent p = new Child();
p.staticMethod();   // "Parent static"  — compile-time reference type wins
p.instanceMethod(); // "Child instance" — runtime type wins (dynamic dispatch)
```

**JVM level:** Overriding uses `invokevirtual` (vtable). Static calls use `invokestatic` — no vtable lookup.

---

### Q2. Can you override a private method? What appears to happen and what is actually happening?

You cannot override a private method. Private methods are **not inherited**. What looks like an override in a subclass is a completely new method with the same name.

```java
class Parent {
    private void secret() { System.out.println("Parent"); }
    void callSecret() { secret(); }  // calls Parent.secret()
}
class Child extends Parent {
    void secret() { System.out.println("Child"); }  // NEW method, not an override
}

new Child().callSecret(); // prints "Parent" — polymorphism does NOT apply
```

`@Override` would cause a compile error here. This is a classic trap in interviews.

---

### Q3. What is a covariant return type? Can an overriding method declare fewer checked exceptions? Prove it.

**Covariant return type** (Java 5+): An overriding method can return a subtype of the parent's return type.

**Exceptions:** An overriding method can throw **fewer or narrower** checked exceptions — never broader.

```java
class Parent {
    Parent getInstance() throws IOException { return new Parent(); }
}
class Child extends Parent {
    @Override
    Child getInstance() throws FileNotFoundException { // covariant return + narrower exception
        return new Child();
    }
}
```

**Why allowed?** Callers using a `Parent` reference expect to handle at most `IOException`. A `FileNotFoundException` is still an `IOException`, so the caller's contract is not violated. Broader exceptions would break the caller's catch block assumptions.

**At bytecode level:** The compiler generates a **bridge method** with the original return type that delegates to the real method. This satisfies the JVM's exact-match requirement for method descriptors.

---

### Q4. Can a constructor be final, static, or abstract? What are the compile-time and semantic reasons?

| Modifier | Allowed | Reason |
|----------|---------|--------|
| `final` | No | Constructors are not inherited; `final` prevents overriding — meaningless here |
| `static` | No | Constructors always operate on a specific new instance; `static` has no `this` context |
| `abstract` | No | `abstract` means "no implementation here, implement in subclass" — nonsensical for a constructor which must have a body |

Constructors are identified by name (same as class name) and have no return type. They are invoked via `invokespecial`, not `invokevirtual` — they don't participate in polymorphism.

---

### Q5. If a subclass constructor omits `super()`, what does the compiler do? What breaks if the parent adds a parameterized constructor?

The compiler **silently inserts `super()`** as the first statement if no explicit `super(...)` or `this(...)` call exists.

**The trap:** If the parent class previously had a no-arg constructor (explicitly or implicitly) and you add a parameterized constructor without keeping the no-arg:

```java
class Parent {
    // Before: implicit no-arg constructor existed
    Parent(String name) { }  // Now: implicit no-arg is GONE
}
class Child extends Parent {
    Child() { }  // Compiler inserts super() — COMPILE ERROR: no suitable constructor
}
```

This is a **common cause of compile failures after refactoring**. The fix is either add `super("default")` in `Child` or restore a no-arg constructor in `Parent`.

---

### Q6. Can you instantiate an abstract class? What is the serialization trap with anonymous subclasses?

You cannot instantiate an abstract class directly. But you can instantiate an **anonymous subclass** of it:

```java
abstract class Template {
    abstract void execute();
}
Template t = new Template() {
    @Override void execute() { System.out.println("anonymous"); }
};
```

**Serialization trap:** Anonymous classes declared inside an instance context hold an **implicit reference (`this$0`)** to the enclosing instance. If you try to serialize the anonymous class object:

1. The enclosing instance must also be `Serializable`
2. The entire enclosing object graph gets dragged into serialization
3. If the enclosing instance is not serializable, you get a `NotSerializableException` — often unexpected

**Memory leak variant:** Anonymous Runnables posted to an executor or stored in a list retain the enclosing instance, preventing GC of the outer object.

---

### Q7. Explain Liskov Substitution Principle (LSP) with a concrete violation that causes a production regression.

**LSP:** If `S` is a subtype of `T`, then objects of type `T` may be replaced with objects of type `S` without altering the correctness of the program.

**Classic violation — Square extends Rectangle:**

```java
class Rectangle {
    int width, height;
    void setWidth(int w)  { this.width = w; }
    void setHeight(int h) { this.height = h; }
    int area() { return width * height; }
}

class Square extends Rectangle {
    @Override void setWidth(int w)  { this.width = w; this.height = w; }  // must stay square
    @Override void setHeight(int h) { this.width = h; this.height = h; }
}

// Code that worked with Rectangle breaks with Square:
Rectangle r = new Square();
r.setWidth(5);
r.setHeight(3);
System.out.println(r.area()); // Expected 15, got 9 — LSP violated
```

**Real production scenario:** A `ReadOnlyList extends ArrayList` that throws `UnsupportedOperationException` on `add()`. Any code doing `List items = getList(); items.add(x);` compiles fine, passes code review, but throws at runtime when `getList()` returns a `ReadOnlyList`. This is why Java's `Collections.unmodifiableList()` wraps rather than extends.

---

### Q8. What is the difference between composition and inheritance at the design and bytecode level?

**Design:**
- Inheritance = IS-A. Hardcodes the relationship at compile time. Tight coupling.
- Composition = HAS-A. Flexible; behavior injected via interface. Loose coupling.

**Bytecode:**
- Inheritance: parent methods live in the child's vtable. `super.method()` compiles to `invokespecial`.
- Composition: delegated object is a field. Calls compile to `invokevirtual` or `invokeinterface` on the field.

```java
// Inheritance — tight coupling, can't change behavior at runtime
class LoggingList extends ArrayList<String> {
    @Override public boolean add(String s) {
        log(s); return super.add(s);
    }
}

// Composition — can swap delegate, mock in tests, change at runtime
class LoggingList<T> implements List<T> {
    private final List<T> delegate;
    LoggingList(List<T> delegate) { this.delegate = delegate; }
    public boolean add(T item) { log(item); return delegate.add(item); }
    // delegate remaining methods...
}
```

**Why inheritance breaks:** `ArrayList` has `addAll()` which calls `add()`. With inheritance and overriding `add()`, `addAll()` now calls your logging `add()` — **double-logging**. This is the classic Bloch "broken counter" example from Effective Java Item 18.

---

## 2. Java Collections Internals

### Q9. Walk through `HashMap.put(key, value)` in Java 8+ — every step, including treeification.

```
Step 1: hash(key)
  - If key == null → hash = 0 (goes to bucket 0)
  - Else: h = key.hashCode(); return h ^ (h >>> 16)
    Why: XOR high 16 bits into low 16 to spread entropy. Table size is always
    a power of 2, so index = (n-1) & hash uses only low bits. Perturbation
    prevents hash functions with poor low-bit distribution from clustering.

Step 2: table index = (n - 1) & hash
  - n = table.length (power of 2). Bitwise AND is faster than modulo.

Step 3: Inspect bucket at index
  a) Bucket empty → create new Node, place it. Check if resize needed.
  b) Bucket has TreeNode → tree insert (O(log n)).
  c) Bucket has LinkedList:
     - Walk the list. If key found (hash matches AND (k == key || key.equals(k))):
       update value, return old value.
     - Else: append new Node at tail.
     - If list length >= TREEIFY_THRESHOLD (8):
       → if table.length < MIN_TREEIFY_CAPACITY (64): resize instead (doubling)
       → else: treeify bucket (convert LinkedList → Red-Black Tree)

Step 4: ++modCount (fail-fast iterator support)

Step 5: if (++size > threshold) resize()
  - threshold = capacity * loadFactor (default 0.75)
  - resize() doubles capacity, rehashes ALL entries (expensive — O(n))
```

**Key missed nuances:**
- Treeification needs **both** ≥8 nodes **and** table size ≥64. Below 64, resize is preferred.
- Java 8 uses **tail insertion** for linked list (vs Java 7's head insertion — which caused infinite loops in concurrent put due to cycle creation during resize).
- The Red-Black Tree **untreeifies** back to a linked list during resize if bucket size drops below `UNTREEIFY_THRESHOLD` (6).

---

### Q10. What happens when you mutate a HashMap key after insertion?

```java
Map<List<String>, Integer> map = new HashMap<>();
List<String> key = new ArrayList<>(Arrays.asList("a", "b"));
map.put(key, 42);

key.add("c");  // mutation changes hashCode

System.out.println(map.get(key));   // null — looks in wrong bucket
System.out.println(map.size());     // 1 — entry still physically present
System.out.println(map.containsValue(42)); // true — entry still there
```

**Why:** After mutation, `key.hashCode()` changes. `get()` computes the new hash, looks in the new bucket — empty. The old entry sits in the original bucket and is now **permanently orphaned**: reachable only by iterating all entries.

**Production impact:** Using mutable domain objects (JPA entities, DTOs) as HashMap keys is a common source of phantom bugs. Use immutable keys (String, Integer, records, value objects).

---

### Q11. How did ConcurrentHashMap change from Java 7 to Java 8? What does `concurrencyLevel` do now?

**Java 7 — Segment-based:**
```
ConcurrentHashMap
├── Segment[0]  (ReentrantLock)  → HashEntry[]
├── Segment[1]  (ReentrantLock)  → HashEntry[]
...
└── Segment[15] (ReentrantLock)  → HashEntry[]
```
- Default 16 segments → 16 parallel writers maximum
- `concurrencyLevel` parameter set the number of segments
- Each segment is an independent mini-HashMap with its own lock
- Reads of volatile `HashEntry.value` are lock-free

**Java 8 — Node array + CAS + synchronized on bin:**
```
ConcurrentHashMap
└── Node[] table (volatile)
     ├── bin[0]: null
     ├── bin[1]: Node → Node → Node  (linked list, synchronized on head)
     ├── bin[2]: TreeBin (Red-Black tree)
     ...
```
- Empty bin: insertion via **CAS** on the Node array slot (no lock at all)
- Non-empty bin: `synchronized(binHead)` — lock is on the first node, not a segment
- Reads: fully **lock-free** (volatile reads)
- `concurrencyLevel` parameter: **ignored** (kept only for API compatibility). The effective concurrency is now proportional to the table size.

**`size()` accuracy:** Java 8 uses a `baseCount` + `CounterCell[]` striped counter (similar to `LongAdder`) to avoid contention on a single counter. `size()` may return a stale value in a concurrent context — use `mappingCount()` which returns `long`.

---

### Q12. Why does ConcurrentHashMap prohibit null keys and values?

**The ambiguity problem:**

```java
ConcurrentHashMap<String, String> map = new ConcurrentHashMap<>();
String value = map.get("key");
// value is null — but WHY?
// Option A: "key" is not in the map
// Option B: "key" IS in the map, its value is null
```

In a **concurrent context**, you cannot use `containsKey()` to disambiguate because the map can change between the two calls. In `HashMap` (single-threaded), you can safely call `containsKey()` right after `get()`. In `ConcurrentHashMap`, that window is a race condition.

**Doug Lea's design decision:** Prohibit null entirely so the return value of `get()` unambiguously means "not present." Null keys have the same problem (null `hashCode()` would require special handling and semantic ambiguity).

---

### Q13. Explain fail-fast vs fail-safe iterators. What is `modCount` and how does it work?

**fail-fast:** Detects concurrent modification during iteration and throws `ConcurrentModificationException`.

```java
// modCount is an int field in ArrayList, HashMap, etc.
// Incremented on every structural modification (add, remove, clear, resize)

ArrayList<String> list = new ArrayList<>(Arrays.asList("a","b","c"));
Iterator<String> it = list.iterator();
// Iterator captures: expectedModCount = list.modCount at creation time

it.next();          // checks: if (modCount != expectedModCount) throw CME
list.add("d");      // modCount++ (now modCount != expectedModCount)
it.next();          // throws ConcurrentModificationException
```

**Important:** `modCount` check is a **best-effort** detection — the JVM makes no guarantees in a multithreaded context (it's not atomic). CME is for detecting **bugs**, not for thread-safety.

**fail-safe (snapshot-based):**
- `CopyOnWriteArrayList`: iterator operates on an immutable array snapshot taken at iterator creation. No CME, but may miss recent writes.
- `ConcurrentHashMap`: iterates the live table (weakly consistent — may or may not reflect concurrent changes, never throws CME).

**Safe removal during iteration (fail-fast collections):**
```java
Iterator<String> it = list.iterator();
while (it.hasNext()) {
    if (condition(it.next())) it.remove(); // calls it.remove() not list.remove()
    // it.remove() updates expectedModCount to match — no CME
}
// Java 8+: list.removeIf(condition) — cleaner
```

---

### Q14. How does `LinkedHashMap` work internally? Describe the LRU cache pattern it enables.

`LinkedHashMap` extends `HashMap` and maintains a **doubly-linked list** running through all entries in insertion order (or access order). Each `Entry` has `before` and `after` pointers in addition to `HashMap`'s `next` pointer for the bucket chain.

**Access-order mode** (`new LinkedHashMap<>(16, 0.75f, true)`): On every `get()` or `put()`, the accessed entry is **moved to the tail** of the doubly-linked list. The head of the list is thus always the **least recently used** entry.

**LRU cache in 3 lines:**
```java
class LRUCache<K, V> extends LinkedHashMap<K, V> {
    private final int maxSize;
    LRUCache(int maxSize) {
        super(16, 0.75f, true); // access-order = true
        this.maxSize = maxSize;
    }
    @Override
    protected boolean removeEldestEntry(Map.Entry<K, V> eldest) {
        return size() > maxSize; // removes LRU entry (head of doubly-linked list)
    }
}
```

**Not thread-safe.** Wrap with `Collections.synchronizedMap()` or use `Caffeine` for production LRU caches.

---

### Q15. What is the time complexity of `PriorityQueue` operations? Explain the heap invariant during `poll()`.

`PriorityQueue` is a **binary min-heap** backed by an `Object[]` array. Parent at index `i`, children at `2i+1` and `2i+2`.

| Operation | Time Complexity |
|-----------|----------------|
| `offer(e)` | O(log n) — sift up |
| `poll()` | O(log n) — sift down |
| `peek()` | O(1) — array[0] |
| `remove(o)` | O(n) — linear scan to find, then O(log n) sift |
| `contains(o)` | O(n) — linear scan |
| Build via `new PriorityQueue<>(collection)` | O(n) — heapify |

**`poll()` mechanics:**
```
Heap: [1, 3, 2, 7, 5, 6, 4]
      root=1 is min

Step 1: Save root (1) to return
Step 2: Move last element (4) to root
        [4, 3, 2, 7, 5, 6]
Step 3: Sift down: compare 4 with children 3 and 2, swap with smaller child (2)
        [2, 3, 4, 7, 5, 6]  (but 4 vs 4/6 — 4 is already ≤ both, stop)
Return: 1
```

**Iteration order is NOT sorted.** `PriorityQueue.iterator()` traverses the array in array order — random-seeming. To get sorted output, poll repeatedly.

---

### Q16. What is the load factor in HashMap? Why 0.75? What happens at 1.0?

**Load factor** = `size / capacity`. Resize triggers when `size > capacity * loadFactor`.

**Why 0.75 (from JDK source comment):** "Because TreeNodes are about twice the size of regular nodes and we want to use them only when bins contain enough nodes to warrant use (see TREEIFY_THRESHOLD). And to avoid conflicts of interest between resizing and treeification thresholds, we require that a table size always be a power of 2, and threshold = (load factor) × capacity. The load factor of 0.75 was chosen after analysis of Poisson distribution to keep expected collisions per bucket below about 1."

**Effect of changing load factor:**

| Load Factor | Tradeoff |
|------------|---------|
| 0.5 | Fewer collisions, lower lookup time, 2× memory waste |
| 0.75 | Balanced (default) |
| 1.0 | Table fills before resize. By Poisson: expected bucket length grows past 1, O(1) amortized degrades toward O(n) |
| > 1.0 | Legal but inadvisable. Multiple guaranteed collisions per slot |

**Pre-sizing for known data volume:**
```java
// Avoid resize when you know you'll add 1000 entries
new HashMap<>(1000 / 0.75 + 1);  // capacity = 1334, won't resize below 1000 entries
// Or: Java Guava
Maps.newHashMapWithExpectedSize(1000);
```

---

## 3. Generics, Type Erasure & Wildcards

### Q17. What is type erasure? What generic information IS preserved in bytecode?

**Type erasure:** The Java compiler removes all generic type parameters at compile time. `List<String>` becomes `List` in bytecode. Type bounds are replaced by their bound type: `T extends Comparable` → `Comparable`; unbounded `T` → `Object`.

**What IS preserved (contrary to popular belief):**

Generic signatures are retained in the `.class` file's `Signature` attribute — but only for **class/interface/method/field declarations**, NOT for local variables or runtime object instances.

```java
class Container<T> {
    private T value;  // Signature attribute says: T
    public T getValue() { return value; }
}

// At runtime:
Class<?> c = Container.class;
Type genericSuperclass = c.getGenericSuperclass(); // java.lang.Object (no param)
Field f = c.getDeclaredField("value");
System.out.println(f.getGenericType()); // T — class-level signature preserved

// But for instances:
Container<String> cs = new Container<>();
// cs.getClass() == Container.class — no String info available
```

**How frameworks exploit preserved signatures:**
```java
// Jackson / Spring / Gson use TypeToken pattern:
TypeToken<List<String>> token = new TypeToken<List<String>>() {};
// Anonymous subclass preserves the generic supertype signature in bytecode
// token.getType() == ParameterizedType(List, [String])
```

---

### Q18. Why can't you create `new T[]`? What are the risks of `(T[]) new Object[]`?

**Arrays are reified** (runtime type is known). Generics are erased (runtime type is unknown). The JVM enforces array type safety at runtime — it must know the component type at creation.

```java
<T> T[] create() {
    return new T[10];         // COMPILE ERROR: generic array creation
    return (T[]) new Object[10]; // compiles with unchecked warning
}

String[] arr = this.<String>create(); // ClassCastException at this assignment
// JVM inserts a checkcast instruction where the array is returned/assigned
// Object[] cannot be cast to String[]
```

**Safe alternative using reflection:**
```java
@SuppressWarnings("unchecked")
<T> T[] create(Class<T> clazz, int size) {
    return (T[]) java.lang.reflect.Array.newInstance(clazz, size);
}
String[] arr = create(String.class, 10); // safe
```

**Why arrays are covariant but this causes problems:**
```java
String[] strings = new String[3];
Object[] objects = strings;      // legal — arrays are covariant
objects[0] = Integer.valueOf(1); // throws ArrayStoreException at RUNTIME
// The JVM checks component type on every array write
```

This is why `List<String>` is NOT a `List<Object>` — generics are invariant by design to prevent this class of bug at compile time.

---

### Q19. Explain PECS. When does each wildcard form make sense? Prove with `Collections.copy()`.

**PECS: Producer Extends, Consumer Super**

```java
// Producer (you READ from it) → ? extends T
// Consumer (you WRITE to it) → ? super T

public static <T> void copy(List<? super T> dest,   // Consumer: you add T into dest
                            List<? extends T> src) { // Producer: you read T from src
    for (int i = 0; i < src.size(); i++)
        dest.set(i, src.get(i));
}
```

**`? extends T` — read-only:**
```java
List<? extends Number> nums = new ArrayList<Integer>();
Number n = nums.get(0);  // OK — guaranteed to be at least Number
nums.add(1);             // COMPILE ERROR — could be List<Double>, can't add Integer
nums.add(null);          // OK — null is always safe
```

**`? super T` — write-friendly:**
```java
List<? super Integer> sink = new ArrayList<Number>();
sink.add(42);            // OK — 42 is Integer, Integer is a super of Integer
sink.add(1L);            // COMPILE ERROR — Long is not Integer or subtype
Object o = sink.get(0);  // can only get Object — type of elements is unknown
```

**When to use in API design:**
- Return type: prefer `? extends T` — callers can read, you don't restrict future impl
- Parameter type: prefer `? super T` — callers can pass broader collections

---

### Q20. Can a class implement the same generic interface twice with different type args?

```java
// COMPILE ERROR:
class Foo implements Comparable<Foo>, Comparable<Bar> { }
// After erasure both become Comparable — duplicate interface
```

**Why it matters:** When serializing, Jackson annotation processors check generic interface implementations. `Foo implements JsonDeserializer<A>, JsonDeserializer<B>` fails for the same reason.

**Workaround:** Use delegation or a wrapper class.

---

### Q21. Distinguish between `List` (raw), `List<?>`, and `List<Object>`.

```java
List raw   = new ArrayList<String>();  // raw type — opt out of generics
List<?>    wild = new ArrayList<String>(); // unbounded wildcard
List<Object> obj = new ArrayList<String>(); // COMPILE ERROR — not assignable

// raw type — you lose all type safety
raw.add("hello");
raw.add(42);  // no warning at source — runtime ClassCastException possible later

// wildcard — safe read-only
wild.add("hello");  // COMPILE ERROR — cannot add to ? wildcard
wild.add(null);     // OK
String s = (String) wild.get(0); // must cast

// List<Object> — can hold anything, but List<String> is NOT assignable to it
List<Object> objects = new ArrayList<>();
objects.add("hello");
objects.add(42);   // OK — Object accepts all
```

**Key rule:** `List<String>` is a `List<?>` (can assign). `List<String>` is NOT a `List<Object>` (invariant).

---

### Q22. Why can't generics use primitive types? What's coming in Project Valhalla?

**Root cause:** Generics work by erasing to `Object`. Primitives (`int`, `double`, `long`) are NOT `Object` — they don't fit in an Object slot. The heap layout of a generic class assumes every element is an object reference (8 bytes on 64-bit).

**Current workaround:** Autoboxing → `List<Integer>`, `Map<Long, Double>`. Causes:
- Heap allocations (GC pressure)
- Cache misses (pointer chasing vs sequential array layout)
- 8x memory overhead for `int` → `Integer`

**Project Valhalla (Java 23+ Preview, full GA in future):**
- **Value classes:** Objects without identity (no `==` comparison on identity), can be inline/flattened
- **Primitive classes:** `primitive class Point { int x; int y; }` — inlined into arrays
- `List<int>` would store `int` values inline — no boxing, cache-friendly, zero GC overhead
- Already partially available as preview via `--enable-preview` in Java 23–25

**Interim solutions for performance:**
- `int[]` over `List<Integer>`
- Eclipse Collections primitives (`IntList`, `LongObjectHashMap`)
- `java.util.stream.IntStream` (primitive stream specializations)

---

## 4. Exception Handling — Edge Cases

### Q23. What does `finally` returning do to a `try` block's return value?

```java
int method() {
    try {
        return 1;
    } finally {
        return 2; // This WINS — suppresses try's return value
    }
}
// method() returns 2 — the 1 is silently discarded
```

**Bytecode explanation:** The compiler saves the `try`'s return value in a temporary variable, then executes `finally`. If `finally` has its own `return`, it replaces the saved value.

**Exception variant:**
```java
int method() {
    try {
        throw new RuntimeException("try");
    } finally {
        return 42; // SWALLOWS the RuntimeException — very dangerous
    }
}
// No exception thrown. Returns 42. The RuntimeException is silently lost.
```

**Rule:** Never use `return`, `break`, or `continue` in a `finally` block.

---

### Q24. What happens when both `catch` and `finally` throw exceptions?

```java
void method() throws Exception {
    try {
        throw new IOException("original");
    } catch (IOException e) {
        throw new RuntimeException("from catch"); // currently propagating this
    } finally {
        throw new IllegalStateException("from finally"); // REPLACES the above
    }
}
// IllegalStateException propagates. RuntimeException from catch is LOST FOREVER.
```

**Java 7+ suppressed exceptions:** `try-with-resources` preserves the original exception and attaches the secondary one as a suppressed exception.

```java
try (Resource r = new Resource()) {
    throw new IOException("primary");  // r.close() also throws RuntimeException
}
// IOException propagates. RuntimeException is attached as suppressed:
// ex.getSuppressed() → [RuntimeException("from close")]
```

```java
// Manually adding suppressed:
Exception primary = new IOException("primary");
Exception secondary = new RuntimeException("secondary");
primary.addSuppressed(secondary);
throw primary;
```

---

### Q25. At the JVM level, what is the difference between checked and unchecked exceptions?

**At the JVM level: NONE.** The JVM has no concept of checked vs unchecked. Both are `Throwable` subclasses. Both can be thrown with `athrow`. The JVM's exception table records handler ranges without caring about exception type hierarchy (beyond matching the listed class).

**Java compiler enforces the distinction.** `throws` declarations are syntactic sugar checked at compile time. This is why:

```java
// Lombok @SneakyThrows uses this — throws a checked exception without declaring it
@SuppressWarnings("unchecked")
static <T extends Throwable> void sneakyThrow(Throwable t) throws T {
    throw (T) t; // unchecked cast at compile time; JVM doesn't care
}

// Usage:
void method() { // no throws clause
    sneakyThrow(new IOException("sneaky"));  // compiles, throws at runtime
}
```

**Stack unwinding:** When an exception is thrown, the JVM scans the exception table of the current frame for a handler. If not found, pops the frame and repeats up the call stack.

---

### Q26. Can you catch `Error`? When is it ever justified?

```java
try {
    riskyOperation();
} catch (Error e) {  // legal, but almost always wrong
    log.error("JVM error", e);
    // Do NOT try to recover — JVM state may be corrupt
}
```

**Justified cases (rare):**

1. **Request-scoped `OutOfMemoryError`:** A web server catching OOM per-request to return HTTP 503 gracefully, after releasing all request-local resources:
   ```java
   try {
       return processRequest(req);
   } catch (OutOfMemoryError e) {
       releaseRequestResources(); // must not allocate
       return Response.serverError().build();
   }
   ```

2. **`AssertionError` in test frameworks:** JUnit catches `AssertionError` (an `Error` subclass) to report failures.

3. **`ThreadDeath`:** Thrown by deprecated `Thread.stop()`. Must be re-thrown to actually stop the thread.

**Never catch:** `VirtualMachineError`, `StackOverflowError` in a recursive path — the JVM state is undefined.

---

### Q27. In what order are resources closed in try-with-resources? What about nested?

```java
try (A a = new A(); B b = new B(); C c = new C()) {
    // use a, b, c
}
// Close order: C → B → A (reverse declaration order)
// If c.close() throws, it becomes the primary exception
// If then b.close() also throws, b's exception is SUPPRESSED on c's exception
```

**Why reverse order?** `C` was created last and depends on `B` which depends on `A`. Closing `C` first ensures no dependent resources access closed upstreams.

**Nested try-with-resources:**
```java
try (InputStream in = new FileInputStream("f");
     InputStreamReader r = new InputStreamReader(in);   // if r throws here,
     BufferedReader br = new BufferedReader(r)) {        // in is still closed
    ...
}
// If InputStreamReader constructor throws: in.close() is called automatically
```

---

## 5. String Internals & String Pool

### Q28. `new String("hello")` — how many objects? Where are they?

```java
String s = new String("hello");
```

**2 objects** (or 1 if "hello" is already pooled):
1. The string literal `"hello"` — in the **String pool** (on the main heap, in Old/Young Gen since Java 7. Was in PermGen pre-Java 7).
2. A **new `String` object** on the regular heap wrapping the same underlying `byte[]`. (Note: the `byte[]` itself may be shared between the two String objects.)

**`s.intern()`** would return the pooled object, and `s.intern() == "hello"` is `true`.

---

### Q29. Explain compile-time string folding and when it doesn't apply.

```java
String s1 = "a" + "b";            // compile-time constant folding → "ab"
String s2 = "ab";
System.out.println(s1 == s2);     // true — same pool entry

final String prefix = "a";
String s3 = prefix + "b";         // final + literal → still constant → "ab"
System.out.println(s2 == s3);     // true — compiler folds final String + literal

String prefix2 = "a";             // NOT final
String s4 = prefix2 + "b";        // runtime concatenation → new object
System.out.println(s2 == s4);     // false

String s5 = "ab";
String s6 = s5 + "";              // runtime concat even with empty string → false
```

**Java 9+ invokedynamic concatenation:** `StringConcatFactory` is invoked at runtime. The result is a new String object unless the JIT optimizes it away. Still `false` for `==` comparisons.

---

### Q30. Why is String immutable? What would break if it were mutable?

**Security:** Class loading uses `String` for class names. If an untrusted component could mutate `"java.lang.String"` to `"evil.MaliciousClass"` after security checks, the JVM could be compromised.

**String pool correctness:** The pool allows multiple references to share one object. If one reference mutates the value, all other holders see the change — catastrophic.

**`hashCode()` caching:** `String` caches its `hashCode` in a field after first computation. Mutation would make the cache stale. All HashMap lookups with String keys would silently break.

**Thread safety:** Immutability makes String inherently thread-safe without synchronization. String references can be freely shared across threads.

**`intern()` pool integrity:** The pool would be unusable if pooled strings were mutable — any reference could corrupt the pool entry for all users.

---

### Q31. What is `String.intern()` and what is its risk at scale?

`intern()` places the string in the JVM's string pool and returns the canonical instance. Useful for reducing duplicates, but risky at scale:

```java
String s = new String("hello");
String pooled = s.intern();
System.out.println(pooled == "hello"); // true
```

**Risks:**
- **Java 6 (PermGen):** The pool is in PermGen with a fixed size. Aggressive interning fills PermGen → OOM.
- **Java 7+ (heap):** Pool is on the heap, GC-eligible. But the pool is backed by a native **StringTable** hash table. With millions of interned strings, the hash table itself consumes significant native memory and causes long GC pauses during StringTable scanning.
- **Not GC-friendly:** Pool entries are strong GC roots until they are no longer referenced AND the class that created them is unloaded.

**Alternatives:**
- `String.deduplicate()` in G1 GC (JVM-managed, no app code needed)
- `Interner<String>` from Guava (heap-based, weak-ref backed)
- Domain-specific enum or interning map with soft values

---

### Q32. `String s = null; s += "hello"` — what prints?

```java
String s = null;
s += "hello";
System.out.println(s); // "nullhello"
```

`+=` desugars to `s = s + "hello"`. String concatenation with null uses `String.valueOf(null)` = `"null"`. This is a frequent source of "nullXxx" appearing in logs or database columns when developers forget null checks.

---

## 6. Java Memory Model (JMM)

### Q33. What does `volatile` guarantee? What does it NOT guarantee? Prove with counter increment.

**`volatile` guarantees:**
1. **Visibility:** Writes are immediately flushed to main memory. Reads always see the latest write from any thread.
2. **Ordering:** Prevents instruction reordering across the volatile access (acts as a memory barrier).

**`volatile` does NOT guarantee atomicity of compound operations:**

```java
volatile int counter = 0;

// Thread 1 and Thread 2 both execute:
counter++;  // NOT atomic — this is: read + increment + write (3 steps)

// Scenario:
// Thread 1 reads: counter = 0
// Thread 2 reads: counter = 0
// Thread 1 writes: counter = 1
// Thread 2 writes: counter = 1  ← lost update
// Expected: 2. Got: 1.

// Fix: Use AtomicInteger
AtomicInteger counter = new AtomicInteger(0);
counter.incrementAndGet(); // CAS — atomic
```

---

### Q34. What is the happens-before relationship? List all sources.

**Happens-before (HB):** If action A happens-before action B, then all memory writes by A (and everything HB A) are visible to B.

**Sources of happens-before ordering:**

| Rule | Description |
|------|-------------|
| Program Order | Within a single thread, each action HB the next action in that thread |
| Monitor Lock | `unlock()` of a monitor HB every subsequent `lock()` of the same monitor |
| `volatile` | Write to a volatile field HB every subsequent read of that field |
| Thread Start | `Thread.start()` HB every action in the started thread |
| Thread Join | All actions in thread T HB return from `T.join()` |
| Thread Interruption | The call to `interrupt()` HB the interrupted thread detecting it |
| Object Construction | Constructor completion HB start of `finalize()` |
| Static Initializer | Static initializer completion HB first use of the class in any thread |
| `Transitivity` | If A HB B and B HB C, then A HB C |

---

### Q35. What is the Double-Checked Locking (DCL) problem? Write the correct fix.

**Broken DCL (without volatile):**
```java
class Singleton {
    private static Singleton instance; // NOT volatile — broken!

    public static Singleton getInstance() {
        if (instance == null) {           // Check 1 (no lock)
            synchronized (Singleton.class) {
                if (instance == null) {   // Check 2 (with lock)
                    instance = new Singleton(); // Problem here
                }
            }
        }
        return instance;
    }
}
```

**Why it's broken:** `instance = new Singleton()` compiles to:
1. Allocate memory
2. Initialize fields
3. Assign reference to `instance`

The JIT/CPU may reorder steps 2 and 3: assign the reference BEFORE fields are initialized. Thread 2 reads a non-null `instance` but sees uninitialized fields.

**Correct fix — add `volatile`:**
```java
private static volatile Singleton instance;
// volatile write establishes HB → prevents reordering
```

**Better fix — static holder idiom (no synchronization needed):**
```java
class Singleton {
    private Singleton() {}
    private static class Holder {
        static final Singleton INSTANCE = new Singleton();
        // Class loading is thread-safe by JVM spec
        // Holder is loaded lazily on first access to INSTANCE
    }
    public static Singleton getInstance() { return Holder.INSTANCE; }
}
```

**Best fix for singletons — use enum:**
```java
enum Singleton {
    INSTANCE;
    // thread-safe, serialization-safe, reflection-safe
}
```

---

### Q36. What is instruction reordering? How does `volatile` prevent it at the hardware level?

**Why CPUs reorder:** Modern CPUs have store buffers, load buffers, and out-of-order execution pipelines. Writes may sit in a store buffer and not reach main memory or L3 cache for many cycles.

```
Thread A:                    Thread B (no synchronization):
x = 1;                       if (ready) {
ready = true;                    assert x == 1; // may FAIL
}                            }
// CPU may reorder: ready=true BEFORE x=1 reaches memory
```

**How `volatile` prevents it (x86 example):**
- Volatile write compiles to a regular store + `LOCK` prefixed instruction (e.g., `lock add [rsp], 0`) or `MFENCE` — a **full memory fence** that flushes the store buffer
- Volatile read compiles to a regular load + `LFENCE` on some architectures (on x86, loads are not reordered so often no explicit fence needed)
- The JIT ensures no reordering of instructions around the volatile access

**JVM-level: 4 types of memory barriers:**
- `LoadLoad` — no load reordered before another load
- `LoadStore` — no load reordered before a store
- `StoreLoad` — no store reordered before a load (most expensive — full fence)
- `StoreStore` — no store reordered before another store

A volatile write inserts `StoreStore` (before) + `StoreLoad` (after). A volatile read inserts `LoadLoad` + `LoadStore` (after).

---

## 7. Reflection & Annotations

### Q37. How do you invoke a private method via reflection? What changed in Java 9+ (modules)?

```java
// Java 8 and earlier — straightforward
Class<?> clazz = SecretService.class;
Method m = clazz.getDeclaredMethod("secretMethod", String.class);
m.setAccessible(true);   // bypasses access check
Object result = m.invoke(instance, "arg");
```

**Java 9+ module system changes:**
- `setAccessible(true)` now also checks the **module system**
- If `SecretService` is in a module that does NOT `opens` its package to your module, `setAccessible(true)` throws `InaccessibleObjectException`
- You must either: add `--add-opens com.target.module/com.target.package=com.your.module` at JVM launch, OR the target module must declare `opens com.target.package;` in its `module-info.java`

**Java 17 — strong encapsulation enforced:**
- Before Java 17, `--add-opens` was a warning. Since Java 17, illegal reflective access is an ERROR.
- Many frameworks (Spring, Hibernate) had to switch from deep reflection to official APIs or `MethodHandle`.

**`MethodHandle` (preferred for performance):**
```java
MethodHandles.Lookup lookup = MethodHandles.privateLookupIn(SecretService.class,
    MethodHandles.lookup()); // requires --add-opens or open module
MethodHandle handle = lookup.findVirtual(SecretService.class, "secretMethod",
    MethodType.methodType(String.class, String.class));
String result = (String) handle.invoke(instance, "arg");
// MethodHandle: JIT-inlinable, ~10x faster than Method.invoke()
```

---

### Q38. What is the difference between `getAnnotation()` and `getDeclaredAnnotation()`? What does `@Inherited` actually apply to?

```java
@Inherited  // only works on CLASS-level annotations
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@interface MyAnnotation {}

@MyAnnotation
class Parent {}
class Child extends Parent {}

// getAnnotation() walks hierarchy if @Inherited:
Child.class.getAnnotation(MyAnnotation.class);         // returns annotation ✓
// getDeclaredAnnotation() only checks the class itself:
Child.class.getDeclaredAnnotation(MyAnnotation.class); // returns null ✗
```

**`@Inherited` limitations (commonly misunderstood):**
- Only works for **class-level annotations**
- Does NOT work for **interface implementations** — annotations on an interface are NOT inherited by implementing classes
- Does NOT work for **method annotations** — a subclass's method doesn't inherit annotations from the overridden parent method

```java
// This does NOT inherit @Transactional from the interface:
interface Service { @Transactional void doWork(); }
class ServiceImpl implements Service { @Override public void doWork() {} }
// ServiceImpl.doWork().getAnnotation(Transactional.class) == null
// This is why Spring uses CGLIB proxy on concrete classes — it re-reads the interface annotation
```

---

### Q39. APT (compile-time annotation processing) vs runtime reflection — explain both with examples.

**APT — Compile-time (javax.annotation.processing):**
```java
@SupportedAnnotationTypes("com.example.AutoRegister")
@SupportedSourceVersion(SourceVersion.RELEASE_21)
public class AutoRegisterProcessor extends AbstractProcessor {
    @Override
    public boolean process(Set<? extends TypeElement> annotations, RoundEnvironment roundEnv) {
        for (Element element : roundEnv.getElementsAnnotatedWith(AutoRegister.class)) {
            generateRegistrationCode(element); // generates source file at compile time
        }
        return true;
    }
}
```
Used by: **Lombok, Dagger, MapStruct, AutoValue, Immutables**
- Zero runtime cost (code generated at build time)
- Type-safe (compiler checks generated code)
- Errors at compile time, not startup

**Runtime Reflection:**
```java
// Spring component scan (simplified)
ClassPathScanningCandidateComponentProvider scanner = new ...;
Set<BeanDefinition> beans = scanner.findCandidateComponents("com.example");
for (BeanDefinition bd : beans) {
    Class<?> clazz = Class.forName(bd.getBeanClassName());
    if (clazz.isAnnotationPresent(Component.class)) {
        registerBean(clazz);
    }
}
```
Used by: **Spring, Hibernate, Jackson, JUnit**
- Flexible (no compile-time dependencies on framework)
- Adds startup time cost (classpath scanning)
- Spring 6 mitigates this with AOT compilation generating reflection metadata upfront

---

## 8. Modern Java Features (Java 8–25)

### Q40. `Optional.orElse()` vs `orElseGet()` — when does `orElse()` cause a silent bug?

```java
Optional<User> user = findUser(id);

// orElse — ALWAYS evaluates the argument, even if Optional is present:
User u1 = user.orElse(createDefaultUser()); // createDefaultUser() ALWAYS called
// If createDefaultUser() has side effects (DB write, logging, metric increment)
// those side effects happen even when the user was found

// orElseGet — Supplier evaluated ONLY if Optional is empty:
User u2 = user.orElseGet(() -> createDefaultUser()); // called ONLY if empty

// Performance example — bad:
return userCache.get(id).orElse(loadFromDatabase(id)); // always hits DB!

// Good:
return userCache.get(id).orElseGet(() -> loadFromDatabase(id)); // lazy
```

**Rule:** If the default value is a constant or cheap: `orElse`. If it involves computation, I/O, or side effects: always `orElseGet`.

---

### Q41. Explain sealed classes in Java 17 and how they enable exhaustive pattern matching. Why does the compiler require exhaustiveness?

```java
// Sealed class — complete hierarchy is known at compile time
sealed interface Shape permits Circle, Rectangle, Triangle {}

record Circle(double radius) implements Shape {}
record Rectangle(double w, double h) implements Shape {}
record Triangle(double base, double height) implements Shape {}

// Pattern matching switch — compiler enforces exhaustiveness:
double area(Shape s) {
    return switch (s) {
        case Circle c        -> Math.PI * c.radius() * c.radius();
        case Rectangle r     -> r.w() * r.h();
        case Triangle t      -> 0.5 * t.base() * t.height();
        // No default needed — compiler KNOWS these are all subtypes
    };
}
```

**Why exhaustiveness matters:** Without sealed, any `switch` on type patterns needs a `default` because new subtypes could appear at runtime (added by a third party or at load time). With sealed, the compiler has a closed world — it can verify all cases are handled and warn/error if you add a new `permits` subtype without updating all switches.

**This enables safe algebraic data types (ADT):** The sealed + record + pattern matching triad gives Java the same expressive power as Kotlin sealed classes or Scala case classes.

**`non-sealed` escape hatch:**
```java
sealed interface Result permits Success, Failure, Pending {}
non-sealed class Pending implements Result {} // anyone can extend Pending
// compiler cannot be exhaustive over Pending subtypes in switches
```

---

### Q42. What is a record? What can and cannot a record do? Compare to Lombok `@Value`.

```java
record Point(int x, int y) {}
// Compiler generates:
// - private final int x, y
// - public Point(int x, int y) (canonical constructor)
// - public int x(), public int y() (accessor methods — NOT getX())
// - equals(), hashCode(), toString() — all based on all components
```

**What records CAN do:**
- Implement interfaces
- Have additional instance methods
- Have static fields and methods
- Have custom constructors (compact, canonical, non-canonical)
- Have `@Override` on `equals`/`hashCode`/`toString`

**What records CANNOT do:**
- Extend any class (implicitly extends `java.lang.Record`, which extends `Object`)
- Declare instance fields outside components
- Have non-final instance fields (all components are `private final`)
- Be `abstract`

**Compact constructor (validation):**
```java
record Range(int min, int max) {
    Range { // compact constructor — parameters implicit
        if (min > max) throw new IllegalArgumentException("min > max");
        // min and max are assigned after this block automatically
    }
}
```

**Records vs Lombok `@Value`:**

| Aspect | Record | Lombok `@Value` |
|--------|--------|-----------------|
| JVM native | Yes — `java.lang.Record`, reflection support | No — compile-time codegen |
| Accessor naming | `x()` not `getX()` | `getX()` |
| Inheritance | Cannot extend classes | Can extend (with caveats) |
| Serialization | Manual `serialVersionUID` not needed (stable) | Needs care |
| Deconstruction pattern | Yes (Java 21+ pattern matching) | No |
| Runtime overhead | Zero | Zero |

---

### Q43. Explain switch expressions vs statements. What is `yield`? What does exhaustiveness mean here?

```java
// Switch STATEMENT (traditional):
int result;
switch (day) {
    case MONDAY: result = 1; break;  // fall-through if no break
    case TUESDAY: result = 2; break;
    default: result = 0;
}

// Switch EXPRESSION (Java 14+, returns a value):
int result = switch (day) {
    case MONDAY  -> 1;   // arrow case — no fall-through, no break needed
    case TUESDAY -> 2;
    default      -> 0;
}; // semicolon required (it's an expression)

// Block case with yield:
int result = switch (day) {
    case MONDAY -> 1;
    case TUESDAY -> {
        log("Tuesday");
        yield 2;  // yield produces the value from a block case
    }
    default -> 0;
};

// Fall-through with traditional case in expressions:
int result = switch (day) {
    case MONDAY, TUESDAY -> 1; // multiple labels per case
    default -> 0;
};
```

**Exhaustiveness:** Switch expressions must cover all possible input values (compiler error if not). For `sealed` types/enums: all variants must be handled or a `default` provided. For `String`/`int`: must have `default`.

---

### Q44. What is `var` (Java 10)? What are its precise limitations?

`var` enables **local variable type inference** — the type is determined by the compiler at compile time. It is NOT `Object`, NOT dynamic typing.

```java
var list = new ArrayList<String>(); // type: ArrayList<String>
var map  = Map.of("a", 1, "b", 2); // type: Map<String, Integer>
var x    = 42;                      // type: int

// Cannot use:
var field;                          // NOT allowed: fields
void method(var param) {}           // NOT allowed: method parameters
var method() { return 1; }         // NOT allowed: return types
var x = null;                       // NOT allowed: cannot infer from null
var x;                              // NOT allowed: must have initializer

// Allowed in lambda (Java 11+) for annotations:
var list = List.of("a", "b");
list.forEach((@NonNull var s) -> System.out.println(s));
```

**Pitfall — widening to interface:**
```java
// var captures the concrete type, not the declared type
var map = new LinkedHashMap<String, Integer>(); // LinkedHashMap, NOT Map
// This gives access to LinkedHashMap-specific methods
// But: if you later change to HashMap, var still compiles — no breakage
```

**Pitfall with diamond in anonymous classes:**
```java
var obj = new Object() { int x = 10; }; // anonymous class with field x
System.out.println(obj.x); // works! var captures the anonymous class type
// Assigning to Object obj2 = obj; loses access to obj.x
```

---

### Q45. Explain text blocks (Java 15). How does indentation stripping work? What are `\s` and `\<newline>`?

```java
String json = """
              {
                "name": "Alice",
                "age": 30
              }
              """; // closing """ sets the indent baseline
```

**Indentation stripping:** The compiler finds the **minimum common leading whitespace** across all non-empty lines and the closing `"""` position — removes that many leading spaces from every line. The closing `"""` position on a new line sets the baseline.

```java
// With closing """ at column 14:
String s = """
              hello
              world
              """;
// → "hello\nworld\n" (14 spaces stripped from each line)

// Shift closing """ to remove more:
String s = """
              hello
          """; // closes at column 10 → strips 10 spaces → "    hello\n"
```

**`\s` — space escape:** Forces a trailing space character. Without it, trailing whitespace is stripped by the compiler.
```java
String s = """
           line1   \s
           line2
           """;
// line1 has a trailing space (preserved by \s)
```

**`\<newline>` — line continuation:** Joins two visual lines into one logical line — no newline in the resulting string.
```java
String s = """
           This is a very long \
           line that continues
           """;
// → "This is a very long line that continues\n"
```

---

### Q46. What are virtual threads (Java 21)? What is pinning and why does it matter?

**Platform thread:** 1:1 with OS thread. Creating thousands is expensive (~1MB stack per thread, kernel scheduling).

**Virtual thread (Project Loom):** M:N user-mode threads. JVM schedules virtual threads onto a pool of `ForkJoinPool` carrier (platform) threads.

```java
// Create 100,000 virtual threads — trivial
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    IntStream.range(0, 100_000).forEach(i ->
        executor.submit(() -> {
            Thread.sleep(Duration.ofSeconds(1)); // unmounts carrier thread during sleep
            return i;
        })
    );
}
```

**Mounting/Unmounting:** When a virtual thread blocks (socket I/O, `Thread.sleep()`, lock), it **unmounts** from the carrier thread. The carrier thread is then free to run other virtual threads. When the blocking operation completes, the virtual thread is rescheduled onto any available carrier.

**Pinning:** A virtual thread is **pinned** (cannot unmount) when:
1. It is inside a `synchronized` block or method
2. It is executing native code (JNI)

A pinned virtual thread **holds the carrier thread** for the duration of the block — blocking the carrier from running other virtual threads.

```java
// Pinning scenario (Java 21):
synchronized (lock) {
    Thread.sleep(1000); // virtual thread is PINNED — carrier thread blocked for 1 second
}

// Fix: use ReentrantLock instead of synchronized:
lock.lock();
try {
    Thread.sleep(1000); // virtual thread can unmount — carrier is free
} finally {
    lock.unlock();
}
```

**Java 24 (JEP 491):** `synchronized` no longer pins virtual threads — the JVM was updated to unmount virtual threads inside synchronized blocks. This removes the main performance concern.

---

### Q47. What is the difference between `ScopedValue` (Java 21) and `ThreadLocal`?

```java
// ThreadLocal — mutable, inheritable, per-thread storage
static ThreadLocal<User> currentUser = new ThreadLocal<>();
currentUser.set(user);
// Must call currentUser.remove() or value leaks across requests in thread pools
// With virtual threads: millions of virtual threads = millions of ThreadLocal entries

// ScopedValue (Java 21+) — immutable, scoped, auto-cleaned
static final ScopedValue<User> CURRENT_USER = ScopedValue.newInstance();

ScopedValue.where(CURRENT_USER, user).run(() -> {
    // CURRENT_USER.get() == user within this scope
    processRequest(); // can be nested — inner scope can shadow outer
});
// After run() returns: value is automatically removed — no leak possible
```

| Aspect | `ThreadLocal` | `ScopedValue` |
|--------|--------------|---------------|
| Mutability | Mutable (can call `set()` anytime) | Immutable within scope (rebind = new scope) |
| Cleanup | Manual (`remove()`) | Automatic (scope exit) |
| Virtual threads | Problematic — survives across request boundaries | Designed for virtual threads |
| Inheritance | `InheritableThreadLocal` for child threads | Inherited into child scopes automatically |
| Performance | Hash lookup per access | Stack-like access — faster |

---

## 9. Serialization — Deep Edge Cases

### Q48. What happens if you don't declare `serialVersionUID`? Exactly when does `InvalidClassException` occur?

The JVM auto-generates `serialVersionUID` as a SHA-1 hash of:
- Class name
- Interface names
- Method signatures
- Field names and types
- Modifiers

**Any structural change** (add/remove field, add method, change modifier, add interface) regenerates the UID → mismatch during deserialization → `InvalidClassException`.

```java
// Always declare explicitly:
class MyClass implements Serializable {
    private static final long serialVersionUID = 1L; // YOU control compatibility
    private String name;
    // Safe to add new fields with a declared UID — they default to their zero value
}
```

**Controlling compatibility:**
- **Changing UID** (e.g., 1L → 2L): Force incompatibility — old serialized data cannot be deserialized
- **Keeping UID**: Added fields deserialize to their default values; removed fields are ignored

---

### Q49. Are `static` fields serialized? What about `transient`? Prove with a test.

```java
class State implements Serializable {
    static int staticCount = 0;      // NOT serialized (belongs to class, not instance)
    transient String password;        // NOT serialized (explicitly excluded)
    String username;                  // serialized
    int loginCount;                   // serialized
}

State s = new State();
s.staticCount = 42;  // class-level
s.password = "secret";
s.username = "alice";
s.loginCount = 5;

// After serialize → deserialize:
// staticCount: value from CURRENT JVM (0 if freshly loaded class, NOT 42)
// password: null (transient default for Object)
// username: "alice" ✓
// loginCount: 5 ✓
```

**`transient` in a different context:** `transient` also works with JPA entities — `@Transient` annotation on a field excludes it from persistence. Same concept, different implementation.

---

### Q50. Explain `readResolve()` and why it's essential for singleton serialization.

```java
class Singleton implements Serializable {
    private static final Singleton INSTANCE = new Singleton();
    private Singleton() {}
    public static Singleton getInstance() { return INSTANCE; }

    // WITHOUT readResolve: deserialization creates a SECOND Singleton instance
    // WITH readResolve: replace deserialized object with the canonical singleton
    private Object readResolve() {
        return INSTANCE; // discard the deserialized object, return the real singleton
    }
}

// Prove it matters:
Singleton s1 = Singleton.getInstance();
// Serialize s1 to bytes...
// Deserialize bytes...
Singleton s2 = /* deserialized */;
System.out.println(s1 == s2); // false WITHOUT readResolve, true WITH it
```

**`writeReplace()`:** Called before serialization. Return a different object to serialize in place of `this`. Used for proxy objects, serialization surrogates.

```java
class HeavyService implements Serializable {
    private Object writeReplace() {
        return new HeavyServiceProxy(this.id); // serialize just the id
    }
}
class HeavyServiceProxy implements Serializable {
    private Object readResolve() {
        return HeavyService.lookup(this.id); // reconstitute on deserialization
    }
}
```

---

### Q51. Can a `Serializable` subclass of a non-`Serializable` parent be safely deserialized?

```java
class NonSerializableParent { // NOT Serializable
    int value = 0;
    NonSerializableParent() { this.value = 10; } // no-arg constructor REQUIRED
}

class SerializableChild extends NonSerializableParent implements Serializable {
    String name;
}
```

**During deserialization:**
1. JVM does NOT call `SerializableChild`'s constructor
2. JVM finds the **first non-Serializable ancestor** (`NonSerializableParent`)
3. Calls that ancestor's **no-arg constructor** to initialize the non-serializable part
4. Then restores `SerializableChild`'s serialized fields

**If no accessible no-arg constructor in `NonSerializableParent`:** `InvalidClassException` at deserialization time.

**Important:** The parent's state (`value = 10`) is NOT restored from the serialized bytes — it's fresh-initialized via the no-arg constructor. Only `SerializableChild`'s own fields are serialized/deserialized.

---

## 10. equals() / hashCode() Contract

### Q52. State the full contract. What breaks when each rule is violated?

**Contract:**
1. **Reflexive:** `x.equals(x)` must be `true`
2. **Symmetric:** `x.equals(y)` ↔ `y.equals(x)`
3. **Transitive:** `x.equals(y)` and `y.equals(z)` → `x.equals(z)`
4. **Consistent:** Multiple calls with unchanged objects return the same result
5. **Null:** `x.equals(null)` must be `false`
6. **hashCode consistency:** If `x.equals(y)` then `x.hashCode() == y.hashCode()`

**Violation consequences:**

| Violation | What breaks |
|-----------|-------------|
| hashCode inconsistent with equals | `HashMap.get()` can't find a key that was `put()`. `HashSet.contains()` returns false for members. |
| Non-reflexive equals | `set.contains(element)` fails for the element's own identity |
| Non-symmetric | `list.contains(x)` depends on which element is the receiver. `list.indexOf(x)` may differ from `list.lastIndexOf(x)` |
| Non-transitive | `TreeSet`/`TreeMap` gives wrong results. `Collections.sort()` is undefined behavior |

---

### Q53. What is the `BigDecimal` `equals()` surprise?

```java
BigDecimal a = new BigDecimal("2.0");
BigDecimal b = new BigDecimal("2.00");

a.equals(b);      // FALSE — different scale (1 vs 2)
a.compareTo(b);   // 0 — same numeric value

// Impact on TreeSet:
TreeSet<BigDecimal> set = new TreeSet<>();
set.add(a);
set.contains(b);  // TRUE — TreeSet uses compareTo, finds them equal
// set.size() == 1 — b was not added (compareTo == 0)

// Impact on HashSet:
HashSet<BigDecimal> hset = new HashSet<>();
hset.add(a);
hset.contains(b); // FALSE — HashSet uses equals, different hash
// hset.size() == 2 — both a and b are added (different equals)
```

This inconsistency between `equals` and `compareTo` in `BigDecimal` is the **only exception** in the Java standard library. Always document your collection choice when storing `BigDecimal`.

---

### Q54. What happens when you put a mutable object in a `HashSet` and mutate it?

```java
class Point {
    int x, y;
    // hashCode based on x and y
}

Set<Point> set = new HashSet<>();
Point p = new Point(1, 2);
set.add(p);          // placed in bucket hash(1,2)

p.x = 99;           // mutation — hashCode changes
set.contains(p);    // FALSE — looks in bucket hash(99,2), finds nothing
set.remove(p);      // FALSE — can't find it to remove
set.size();         // 1 — still there, unfindable
// MEMORY LEAK: p is a permanent ghost in the set
```

**Interview follow-up:** "How would you fix this?" — Either:
1. Use an immutable value object (record, final fields)
2. Base `hashCode()` on only immutable fields (identity-based, not value-based)
3. Use `IdentityHashMap` / `System.identityHashCode()` if you truly need reference equality

---

## 11. Inner Classes, Lambdas & Functional Interfaces

### Q55. What hidden reference does an inner class hold? What leak pattern does this create?

```java
class Outer {
    private byte[] largeBuffer = new byte[1024 * 1024]; // 1MB

    class Inner implements Runnable {
        // Implicitly holds: Outer.this (the this$0 reference)
        public void run() { }
    }

    Runnable createRunnable() {
        return new Inner(); // returns Inner, which holds a ref to Outer
    }
}

// Usage:
Outer outer = new Outer();
Runnable r = outer.createRunnable();
outer = null; // We think Outer is eligible for GC...
// But: r holds Inner, Inner holds Outer.this — 1MB NOT collected
```

**Fix:** Use `static` nested class:
```java
static class Inner implements Runnable {
    // NO Outer.this reference
    public void run() { }
}
```

**Or a lambda (lambdas only capture what they USE):**
```java
Runnable r = () -> { }; // captures nothing — Outer can be GC'd
```

---

### Q56. What is "effectively final"? Can a lambda capture a mutable variable?

```java
void method() {
    int count = 0;          // effectively final — never reassigned
    Runnable r = () -> System.out.println(count); // OK

    count = 1;              // now NOT effectively final
    Runnable r2 = () -> System.out.println(count); // COMPILE ERROR
}
```

**Why:** Local variables live on the stack. When a lambda outlives the method (e.g., submitted to an executor), the stack frame is gone. The JVM **copies** the value into the lambda's instance. If the variable were mutable, the copy would become stale — misleading semantics.

**Workarounds:**
```java
// 1. Array (single-element mutable container)
int[] count = {0};
Runnable r = () -> count[0]++;  // works but ugly

// 2. AtomicInteger
AtomicInteger count = new AtomicInteger(0);
Runnable r = () -> count.incrementAndGet(); // clean, thread-safe

// 3. Redesign — often best
```

---

### Q57. What exactly makes an interface a functional interface? Which `Object` methods are excluded?

A **functional interface** (SAM — Single Abstract Method) has exactly one abstract method NOT already provided by `Object`.

```java
@FunctionalInterface
interface Printer {
    void print(String s);              // 1 abstract method — OK
    default void println(String s) { System.out.println(s); } // default — doesn't count
    static Printer noOp() { return s -> {}; }                 // static — doesn't count
    boolean equals(Object o);          // Object method — does NOT count as abstract
    String toString();                 // Object method — does NOT count as abstract
    int hashCode();                    // Object method — does NOT count as abstract
}
// Result: still a valid @FunctionalInterface (only print() is truly abstract)
```

**Why Object methods excluded?** Every implementing class already has `equals`, `hashCode`, `toString` from `Object`. They are always concretely implemented — they're never truly abstract at the object level.

---

## 12. Autoboxing & Integer Cache Pitfalls

### Q58. Explain the Integer cache. What is the exact range and can it be changed?

```java
Integer a = 127;  Integer b = 127;  System.out.println(a == b); // true
Integer x = 128;  Integer y = 128;  System.out.println(x == y); // false
```

`Integer.valueOf()` (which autoboxing uses) caches instances for `-128` to `127` inclusive. This range is specified in the JLS.

**Upper bound is configurable:**
```bash
-XX:AutoBoxCacheMax=1000  # cache -128 to 1000
```
After this flag: `Integer.valueOf(500) == Integer.valueOf(500)` → `true`.

**Only applies to `Integer`.** `Long`, `Short`, `Byte` also have caches for `-128` to `127` but their upper bounds are NOT configurable. `Double` and `Float` have NO cache.

```java
Long a = 100L;  Long b = 100L;    System.out.println(a == b); // true (cached)
Long x = 1000L; Long y = 1000L;   System.out.println(x == y); // false
Double d1 = 1.0; Double d2 = 1.0; System.out.println(d1 == d2); // false (no cache)
```

---

### Q59. What happens in unboxing with `null`? Name all the places this causes NullPointerException.

```java
Integer i = null;

// Scenario 1: unbox assignment
int x = i;                // NullPointerException

// Scenario 2: arithmetic
int y = i + 1;            // NullPointerException

// Scenario 3: switch
switch (i) { ... }        // NullPointerException (switches on int, triggers unbox)

// Scenario 4: comparison with primitive
if (i == 0) { }           // NullPointerException (unboxes i to int)

// Scenario 5: method parameter
void method(int n) { }
method(i);                // NullPointerException at call site

// Scenario 6: ternary with mixed types
int z = (condition) ? i : 0;  // if i is null → NullPointerException
// Ternary promotes to int (primitive) since one operand is int → unboxes Integer
```

**Helpful NullPointerException (Java 14+):** `NullPointerException: Cannot unbox the return value of the method 'Integer getCount()'` — the JVM now tells you exactly what was null.

---

## 13. Enums — Internals & Patterns

### Q60. How is an enum implemented at the bytecode level?

```java
enum Day { MONDAY, TUESDAY, WEDNESDAY }
```

Compiles to roughly:
```java
final class Day extends java.lang.Enum<Day> {
    public static final Day MONDAY   = new Day("MONDAY",   0);
    public static final Day TUESDAY  = new Day("TUESDAY",  1);
    public static final Day WEDNESDAY= new Day("WEDNESDAY",2);
    private static final Day[] $VALUES = { MONDAY, TUESDAY, WEDNESDAY };

    private Day(String name, int ordinal) { super(name, ordinal); }
    public static Day[] values()   { return $VALUES.clone(); }
    public static Day valueOf(String name) { ... }
}
```

**Singleton guarantee:**
- Class is `final` — cannot be subclassed
- Instances created during class loading — class initialization is thread-safe by JVM spec
- Enum constants are static finals — initialized once

---

### Q61. Can an enum have abstract methods? Demonstrate the pattern.

```java
enum Operation {
    PLUS {
        @Override public double apply(double x, double y) { return x + y; }
    },
    MINUS {
        @Override public double apply(double x, double y) { return x - y; }
    },
    TIMES {
        @Override public double apply(double x, double y) { return x * y; }
    };

    public abstract double apply(double x, double y); // each constant implements this
}

// Usage — no instanceof, no switch needed:
double result = Operation.PLUS.apply(3, 4); // 7.0
```

**This IS the Strategy pattern built into an enum.** No factory needed; each constant IS the strategy.

---

### Q62. Why is `Enum.values()` problematic in performance-critical code?

```java
// Every call to values() creates a NEW clone of the backing array:
for (Day d : Day.values()) { }  // allocates new Day[3] every loop
```

**In tight loops or hot paths:**
```java
// Cache it — standard pattern:
private static final Day[] DAYS = Day.values();  // clone once
for (Day d : DAYS) { }  // no allocation

// Or use EnumSet for iteration:
for (Day d : EnumSet.allOf(Day.class)) { } // backed by long bitmask — no array
```

---

## 14. Interface Evolution (Java 8–25)

### Q63. How is the diamond problem resolved when two interfaces have conflicting default methods?

```java
interface A {
    default void greet() { System.out.println("Hello from A"); }
}
interface B {
    default void greet() { System.out.println("Hello from B"); }
}

class C implements A, B {
    // COMPILE ERROR without explicit override:
    // "class C inherits unrelated defaults for greet() from types A and B"

    @Override
    public void greet() {
        A.super.greet(); // explicitly delegate to A's default
        // or B.super.greet()
        // or provide entirely new implementation
    }
}
```

**Class always wins over interface default:**
```java
class D extends C implements A {
    // C.greet() is inherited — C's concrete method wins over A's default
    // No compilation conflict
}
```

**Interface with more specific override wins over less specific:**
```java
interface A { default void m() {} }
interface B extends A { default void m() {} } // more specific
class C implements A, B {} // B.m() wins — no conflict (B is more specific than A)
```

---

### Q64. What are private interface methods (Java 9)? What problem do they solve?

```java
interface Validator<T> {
    boolean isValid(T value);
    boolean isNotNull(T value);
    boolean isNotEmpty(T value);

    // WITHOUT private methods — code duplication between defaults:
    default boolean validate(T value) {
        return isValid(value) && isNotNull(value) && isNotEmpty(value);
    }
    default boolean validateAndLog(T value) {
        // have to duplicate the logic or make a helper default (pollutes API)
        boolean result = isValid(value) && isNotNull(value) && isNotEmpty(value);
        log(result);
        return result;
    }

    // WITH private method — shared helper without API pollution:
    private boolean allChecks(T value) {
        return isValid(value) && isNotNull(value) && isNotEmpty(value);
    }
    default boolean validate(T value) { return allChecks(value); }
    default boolean validateAndLog(T value) {
        boolean r = allChecks(value); log(r); return r;
    }
    private static void log(boolean result) { ... } // private static also allowed
}
```

**Key point:** Private interface methods are NOT part of the public API. Implementing classes cannot call them. They exist solely for DRY within the interface's default/static methods.

---

## 15. Comparable vs Comparator — Deep

### Q65. What does "consistent with equals" mean? What breaks when it's violated?

**Definition:** `compareTo()` returns 0 if and only if `equals()` returns `true`.

**`BigDecimal` violation:**
```java
BigDecimal a = new BigDecimal("2.0");  // scale=1
BigDecimal b = new BigDecimal("2.00"); // scale=2

a.equals(b);     // false (different scale)
a.compareTo(b);  // 0 (same numeric value)
```

**Impact:**

| Collection | Uses | Result with BigDecimal |
|------------|------|----------------------|
| `HashSet<BigDecimal>` | `equals()` + `hashCode()` | Both 2.0 and 2.00 stored (different hash) |
| `TreeSet<BigDecimal>` | `compareTo()` | Only one stored (compareTo==0 means equal) |
| `HashMap<BigDecimal,V>` | `equals()` + `hashCode()` | Can have two keys 2.0 and 2.00 |
| `TreeMap<BigDecimal,V>` | `compareTo()` | Key 2.0 and 2.00 are same key |

**Silent data loss:** If you switch from `HashMap` to `TreeMap` with `BigDecimal` keys, entries start disappearing.

---

### Q66. What is the integer subtraction anti-pattern in Comparator? Show the overflow bug.

```java
// BUG — common in handwritten comparators:
Comparator<Integer> wrong = (a, b) -> a - b;

// Overflow scenario:
int a = Integer.MIN_VALUE; // -2,147,483,648
int b = 1;
int diff = a - b; // overflows to 2,147,483,647 (Integer.MAX_VALUE)
// Returns positive — means a > b. WRONG. a (-2B) < b (1)

// Correct:
Comparator<Integer> right = Integer::compare; // or (a, b) -> Integer.compare(a, b)
```

---

### Q67. Show the idiomatic Java 8+ multi-field Comparator and what happens with null fields.

```java
record Employee(String lastName, String firstName, int age) {}

// Multi-field comparator:
Comparator<Employee> comp = Comparator
    .comparing(Employee::lastName)
    .thenComparing(Employee::firstName)
    .thenComparingInt(Employee::age);

// With null-safety:
Comparator<Employee> nullSafe = Comparator
    .comparing(Employee::lastName,  Comparator.nullsFirst(Comparator.naturalOrder()))
    .thenComparing(Employee::firstName, Comparator.nullsLast(Comparator.naturalOrder()))
    .thenComparingInt(Employee::age);

// Reversed:
Comparator<Employee> reversed = comp.reversed();

// Composing at stream:
employees.stream()
    .sorted(comp)
    .toList();
```

---

## 16. Classic Gotchas & Output Prediction

### Q68. `System.out.println(1 + 2 + "3" + 4 + 5)` — what prints?

```java
System.out.println(1 + 2 + "3" + 4 + 5); // "3345"
```
Left to right: `1+2=3` → `3+"3"="33"` → `"33"+4="334"` → `"334"+5="3345"`.

```java
System.out.println("" + 1 + 2 + "3" + 4 + 5); // "12345"
```
Starts with String → all concatenation.

```java
System.out.println("1" + (2 + 3)); // "15"
```
Parentheses force int addition first.

---

### Q69. What does `List.of()` vs `Arrays.asList()` vs `new ArrayList<>()` give you?

```java
List<String> a = List.of("a", "b");           // Java 9+: truly IMMUTABLE
List<String> b = Arrays.asList("a", "b");     // fixed-size, MUTABLE elements
List<String> c = new ArrayList<>(List.of("a","b")); // fully mutable

a.add("c");    // UnsupportedOperationException
a.set(0, "x"); // UnsupportedOperationException

b.add("c");    // UnsupportedOperationException (fixed size)
b.set(0, "x"); // OK — can change elements, just not size

c.add("c");    // OK
c.set(0, "x"); // OK

// Null behavior:
List.of(null);         // NullPointerException — nulls prohibited
Arrays.asList(null);   // OK — returns [null]

// contains(null):
List.of("a").contains(null);  // NullPointerException
Arrays.asList("a").contains(null); // false (no NullPointerException)
```

---

### Q70. What is the output? (`try` with `System.exit()` in finally)

```java
try {
    System.out.println("try");
    System.exit(0);
} finally {
    System.out.println("finally"); // Does this print?
}
```

**"try" prints. "finally" does NOT print.** `System.exit()` terminates the JVM immediately. `finally` blocks do NOT run after `System.exit()`.

**Shutdown hooks** (added via `Runtime.getRuntime().addShutdownHook(thread)`) DO run after `System.exit()`.

---

### Q71. What is the ConcurrentModificationException trap with `for-each`?

```java
List<String> list = new ArrayList<>(Arrays.asList("a", "b", "c"));

// WRONG:
for (String s : list) {
    if (s.equals("b")) list.remove(s); // throws ConcurrentModificationException
}

// CORRECT options:
// 1. Iterator with remove:
Iterator<String> it = list.iterator();
while (it.hasNext()) {
    if (it.next().equals("b")) it.remove();
}

// 2. removeIf (Java 8+):
list.removeIf(s -> s.equals("b")); // cleanest

// 3. Collect and remove:
List<String> toRemove = list.stream().filter(s -> s.equals("b")).toList();
list.removeAll(toRemove);
```

---

### Q72. What happens with `String.format()` vs `+` concatenation in a loop?

```java
// SLOW: O(n²) — new StringBuilder created for each + in each iteration
String result = "";
for (int i = 0; i < 10000; i++) {
    result = result + i; // creates 10000 intermediate String objects
}

// FAST: O(n) — single StringBuilder
StringBuilder sb = new StringBuilder();
for (int i = 0; i < 10000; i++) {
    sb.append(i);
}
String result = sb.toString();

// Modern Java: the JIT recognizes + outside loops and optimizes to StringBuilder
// But INSIDE loops, the JIT generally cannot merge across iterations
// EXCEPT: Java 9+ StringConcatFactory with invokedynamic — still creates per-loop object
```

**Interview follow-up:** Why is `StringBuilder` not thread-safe but `StringBuffer` is? When would you use `StringBuffer` today? (Answer: Almost never — use `StringBuilder` + external synchronization.)

---

## Quick Reference — Most Common Violations by Category

```
equals/hashCode:
  • Override equals → must override hashCode (same fields)
  • Never use mutable fields in hashCode for Map/Set keys
  • BigDecimal: use compareTo() not equals() for value comparison

String:
  • Never compare with ==; always .equals()
  • new String("x") creates heap object; "x" may be in pool
  • String += in loops → use StringBuilder

Generics:
  • Never use raw types in new code
  • PECS: ? extends for reading, ? super for writing
  • Cannot create generic arrays

Collections:
  • HashMap key mutation = silent data loss
  • ConcurrentHashMap: no null keys or values
  • Iterator.remove() is safe; list.remove() inside for-each is not

Modern Java:
  • orElse() always evaluates; orElseGet() is lazy
  • var is compile-time type inference, NOT dynamic typing
  • Records cannot extend classes; are implicitly final
  • sealed + record + switch = safe ADT pattern
  • Virtual threads + synchronized = pinning (fixed in Java 24)
```
