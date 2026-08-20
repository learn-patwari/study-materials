# Java Streams & Functional Programming — Interview Prep

> Target: 10–15 YOE · Staff / Senior Engineer
> Companies: Google, Amazon, JP Morgan, Goldman Sachs, Uber, Flipkart, Atlassian, Razorpay

---

## 1. Stream Pipeline Internals

### Q1. How does a stream pipeline execute internally? Walk through the lifecycle.

A stream pipeline is a lazy, single-pass chain: **source → zero or more intermediate operations → one terminal operation**. Nothing executes until the terminal operation is called.

```
source.filter(...).map(...).collect(...)
  ↑ building the pipeline  ↑ triggers execution
```

Internally, each intermediate operation wraps the previous pipeline in a `StatelessOp` or `StatefulOp` subclass of `AbstractPipeline`. Calling `collect()` (or any terminal op) invokes `evaluate()` on the pipeline, which builds a `Sink` chain in reverse order (from terminal back to source), then iterates the source, pushing elements through the chain.

**Key insight:** The pipeline makes **one pass** over the source data (for stateless pipelines). A `filter` + `map` + `collect` processes each element through filter → map → collect before moving to the next element — not filter all elements first, then map all, etc.

**Follow-up gotcha:** `sorted()` and `distinct()` are **stateful** — they buffer all elements before passing any downstream, which breaks the single-pass model.

---

### Q2. What is lazy evaluation and how do you prove it?

Lazy evaluation means intermediate operations do not execute until a terminal operation is called. You can prove it with `peek()`:

```java
List<String> result = List.of("a", "bb", "ccc", "dddd")
    .stream()
    .filter(s -> {
        System.out.println("filter: " + s);
        return s.length() > 2;
    })
    .map(s -> {
        System.out.println("map: " + s);
        return s.toUpperCase();
    })
    .collect(Collectors.toList());

// Output:
// filter: a
// filter: bb
// filter: ccc
// map: ccc
// filter: dddd
// map: dddd
```

Notice: `map` is only called for elements that pass `filter`. With a list vs stream — a list would require two full passes (filter all, then map all). The stream fuses the operations and processes each element completely before moving to the next.

**Production relevance:** For a stream of 10M records, lazy evaluation means you stop processing as soon as a short-circuit terminal (`findFirst`, `anyMatch`) is satisfied — you may process only the first element.

---

### Q3. What is a Spliterator and how does the stream use it?

`Spliterator` (Splittable Iterator) is the mechanism underlying all stream sources. It replaces `Iterator` for streams, adding:
1. `tryAdvance(Consumer)` — process one element
2. `forEachRemaining(Consumer)` — process all remaining elements
3. `trySplit()` — split into two Spliterators for parallel processing

**Characteristics** (bit flags on the Spliterator that guide stream optimization):

| Characteristic | Meaning | Optimization unlocked |
|---|---|---|
| `ORDERED` | Elements have defined encounter order | `findFirst` is deterministic |
| `SIZED` | Size is known upfront | `count()` short-circuits |
| `DISTINCT` | No duplicate elements | `distinct()` is a no-op |
| `SORTED` | Elements are sorted | `sorted()` is a no-op |
| `IMMUTABLE` | Source won't change during traversal | No interference checking |
| `CONCURRENT` | Can be modified concurrently | Safe for parallel streams |
| `NONNULL` | No null elements | Null checks skipped |
| `SUBSIZED` | `trySplit()` produces SIZED parts | Even parallel splits |

```java
List<String> list = List.of("a", "b", "c");
Spliterator<String> sp = list.spliterator();
System.out.println(sp.characteristics()); 
// ORDERED | SIZED | SUBSIZED | IMMUTABLE — 16464
```

**Interview follow-up:** ArrayList has `ORDERED + SIZED + SUBSIZED`. HashSet has only `DISTINCT + SIZED`. This is why `distinct()` on a `Set` stream is a no-op — the stream detects the `DISTINCT` characteristic.

---

### Q4. How many passes does a stream pipeline make over the data?

**One pass** for purely stateless pipelines (filter + map + flatMap + peek combinations).

**Multiple logical passes** for stateful operations:
- `sorted()` — buffers all elements, sorts them, then continues. Effectively a full pass before passing to downstream.
- `distinct()` — uses a `HashSet` internally, buffers to track seen elements.
- `limit(n)` — is short-circuiting (stops after n elements), not a full extra pass.

```java
// This makes one pass:
stream.filter(x -> x > 0).map(x -> x * 2).collect(toList())

// This makes 1.5 passes (sort buffers all, then passes through):
stream.sorted().filter(x -> x > 0).collect(toList())

// Optimization: push filter BEFORE sorted to reduce sort cost:
stream.filter(x -> x > 0).sorted().collect(toList())
```

**Production rule:** Put stateless filters before stateful ops (`sorted`, `distinct`) to minimize the number of elements that need buffering.

---

### Q5. Internal iteration vs external iteration — why do streams win for optimization?

**External iteration (for-each/iterator):** The caller controls the loop. The JVM cannot reorder or fuse operations.
```java
for (String s : list) {
    if (s.length() > 3) result.add(s.toUpperCase());
}
```

**Internal iteration (streams):** The library controls the loop. It can:
1. **Fuse operations** into a single pass (filter + map processed per element)
2. **Short-circuit** early (stop as soon as a condition is met)
3. **Parallelize** by splitting the Spliterator without changing the code
4. **Optimize based on characteristics** (skip `distinct()` if source is a Set)

The caller only declares *what* to compute, not *how* — this is the functional contract that enables these optimizations.

---

## 2. Intermediate Operations Deep Dive

### Q6. What is the difference between `map` and `flatMap`?

`map` applies a 1-to-1 transformation: each input element produces exactly one output element.
`flatMap` applies a 1-to-many transformation: each input element produces a Stream of zero or more output elements, which are then flattened.

```java
// map: List<String> → Stream<Integer> (one length per string)
List<String> words = List.of("hello", "world");
List<Integer> lengths = words.stream()
    .map(String::length)
    .collect(Collectors.toList()); // [5, 5]

// flatMap: List<String> → Stream<String> (multiple chars per string, flattened)
List<List<String>> nested = List.of(
    List.of("a", "b"),
    List.of("c", "d", "e")
);
List<String> flat = nested.stream()
    .flatMap(Collection::stream)
    .collect(Collectors.toList()); // [a, b, c, d, e]
```

**Classic interview problem:**
```java
// Find all unique words across all sentences
List<String> sentences = List.of("hello world", "java streams", "hello java");
Set<String> uniqueWords = sentences.stream()
    .flatMap(s -> Arrays.stream(s.split(" ")))
    .collect(Collectors.toSet()); // {hello, world, java, streams}
```

**Key difference:** `map(f)` where `f` returns a `Stream` would give `Stream<Stream<T>>`. `flatMap` merges those nested streams into a single `Stream<T>`.

---

### Q7. When does `mapMulti` (Java 16) outperform `flatMap`?

`mapMulti` is a push-based alternative to `flatMap` that avoids creating an intermediate Stream for each element:

```java
// flatMap: creates a new Stream for each element (allocation overhead)
stream.flatMap(x -> Stream.of(x, x * 2, x * 3))

// mapMulti: pushes elements into a consumer (no intermediate stream allocation)
stream.<Integer>mapMulti((x, consumer) -> {
    consumer.accept(x);
    consumer.accept(x * 2);
    consumer.accept(x * 3);
})
```

**When `mapMulti` wins:**
1. Each element produces very few output elements (0–3) — the Stream creation overhead of `flatMap` dominates
2. The number of outputs is determined at runtime (conditional pushing)
3. The output type changes (e.g., filtering + mapping in one step)

```java
// Conditional: only emit the parsed int if the string is a valid number
List<String> inputs = List.of("1", "two", "3", "four", "5");
List<Integer> numbers = inputs.stream()
    .<Integer>mapMulti((s, consumer) -> {
        try { consumer.accept(Integer.parseInt(s)); } catch (NumberFormatException ignored) {}
    })
    .collect(Collectors.toList()); // [1, 3, 5]
```

**When `flatMap` wins:** When the sub-stream is large or already exists (e.g., `collection.stream()`). `flatMap` can delegate to the sub-spliterator's `trySplit()` for parallel execution; `mapMulti` cannot.

---

### Q8. What is the stateful vs stateless distinction among intermediate operations?

**Stateless operations:** Process each element independently. Can be fused into a single pass. Safe for parallel execution without coordination.
- `filter`, `map`, `flatMap`, `mapMulti`, `peek`, `mapToInt`, `mapToObj`

**Stateful operations:** Must observe multiple (or all) elements before producing output. Break the single-pass model and require buffering.
- `sorted()` — buffers all elements to sort
- `distinct()` — maintains a seen-set
- `limit(n)` — counts elements (but is also short-circuiting)
- `skip(n)` — counts elements

**Parallel implications:** Stateful operations in parallel streams require coordination:
```java
// distinct() in parallel must merge seen-sets from all threads — expensive
parallelStream().distinct().collect(toList())

// sorted() in parallel buffers everything into one array, then sorts
parallelStream().sorted().collect(toList())
```

**Rule of thumb:** Put stateless filters before stateful ops. If you need `distinct()` on a large parallel stream, consider using a `ConcurrentHashMap.newKeySet()` approach in a custom collector instead.

---

### Q9. What is the purpose of `peek` and why shouldn't it be used for side effects?

`peek` is designed as a debugging tool — it executes a Consumer on each element as it passes through, without modifying the element.

```java
// Correct use: debugging pipeline
List<String> result = stream
    .filter(s -> s.length() > 3)
    .peek(s -> System.out.println("After filter: " + s))
    .map(String::toUpperCase)
    .peek(s -> System.out.println("After map: " + s))
    .collect(Collectors.toList());
```

**Why not for side effects:**
1. `peek` is an intermediate operation and is lazy — if the terminal operation short-circuits, `peek` may never execute for some elements.
2. In parallel streams, `peek` callbacks execute on multiple threads — requires thread-safe side effects.
3. The JVM or stream implementation may skip `peek` calls on `count()` in Java 9+ when size is known from SIZED characteristic.

```java
// Dangerous: count() may short-circuit and skip peek in Java 9+
long count = stream.peek(System.out::println).count(); // unreliable
```

**Production rule:** Use `forEach` for intentional side effects, `peek` only for debug logging that you'll remove before committing.

---

### Q10. How do `takeWhile` and `dropWhile` (Java 9) behave on ordered vs unordered streams?

`takeWhile(predicate)` — takes elements from the stream as long as the predicate holds, then stops.
`dropWhile(predicate)` — drops elements as long as the predicate holds, then passes remaining elements through.

```java
List<Integer> nums = List.of(1, 2, 3, 4, 5, 4, 3);

// takeWhile: stops at first false
nums.stream().takeWhile(n -> n < 4).collect(toList()); // [1, 2, 3]

// dropWhile: drops until first false, then passes all remaining
nums.stream().dropWhile(n -> n < 4).collect(toList()); // [4, 5, 4, 3]
```

**On unordered streams:** Behavior is nondeterministic. For an unordered stream, `takeWhile` may return any subset of elements that satisfy the predicate — not necessarily the first contiguous run. This is surprising:

```java
Set<Integer> set = new HashSet<>(Set.of(1, 2, 3, 4, 5));
// Unordered: encounter order undefined
set.stream().takeWhile(n -> n < 4).collect(toList()); // any subset of {1,2,3}
```

**Production use case:** Reading a sorted log file until a timestamp threshold:
```java
Files.lines(Path.of("app.log"))
    .takeWhile(line -> !line.startsWith("2024-12-31"))
    .collect(toList());
```

---

## 3. Terminal Operations & Short-Circuiting

### Q11. Which terminal operations are short-circuiting and why?

Short-circuit terminal operations can produce a result without processing all elements:

| Operation | Short-circuits when |
|---|---|
| `findFirst()` | First element found |
| `findAny()` | Any element found (parallel-friendly) |
| `anyMatch(p)` | First element matching p |
| `noneMatch(p)` | First element matching p (then returns false) |
| `allMatch(p)` | First element NOT matching p |
| `limit(n)` | n elements accumulated (intermediate, but also short-circuits) |

```java
// Short-circuits after finding first even number:
Optional<Integer> first = Stream.iterate(1, n -> n + 1)
    .filter(n -> n % 2 == 0)
    .findFirst(); // returns Optional[2] — doesn't iterate forever
```

**Non-short-circuit terminals:** `collect`, `reduce`, `forEach`, `count`, `min`, `max`, `toArray` — must process all elements.

**Interview gotcha:** `count()` on a `SIZED` stream (e.g., from an ArrayList) is optimized to return the size directly without iterating — so it's effectively O(1) even though it's not technically "short-circuiting."

---

### Q12. Explain `reduce` — identity, combiner, and why mutable state is wrong.

`reduce` has three forms:

```java
// Form 1: identity + accumulator (always returns T)
int sum = IntStream.rangeClosed(1, 10).reduce(0, Integer::sum); // 55

// Form 2: no identity (returns Optional — empty stream case)
Optional<Integer> max = Stream.of(3, 1, 4, 1, 5).reduce(Integer::max);

// Form 3: identity + accumulator + combiner (for parallel + type change)
int totalLen = Stream.of("hello", "world")
    .reduce(0, (acc, s) -> acc + s.length(), Integer::sum); // 10
```

**Identity contract:** The identity value must satisfy `identity combiner element == element` for all elements. Using wrong identity breaks parallel reduce:
```java
// Wrong: 1 is not identity for multiplication if any element could be 0
stream.reduce(1, (a, b) -> a * b) // works accidentally if no 0s
// Correct identity for multiplication is 1, which satisfies 1*x == x ✓
```

**Why mutable state is wrong with reduce:**
```java
// BROKEN: shared StringBuilder in parallel stream = race condition
StringBuilder sb = stream.parallel().reduce(new StringBuilder(), 
    (acc, s) -> acc.append(s), // wrong: mutating shared container
    StringBuilder::append);

// CORRECT: use collect with a Collector — designed for mutable accumulation
String result = stream.collect(Collectors.joining());
```

**Rule:** `reduce` is for **immutable** combination (producing a new value each step). For **mutable** accumulation (building a list, map, string), use `collect`.

---

### Q13. What is the difference between `forEach` and `forEachOrdered` in parallel streams?

`forEach` — no ordering guarantee. In parallel streams, elements are processed in whichever order threads pick them up. Faster.
`forEachOrdered` — guarantees encounter order is respected. In parallel streams, forces a merge step to serialize output in source order. Slower.

```java
IntStream.range(1, 6).parallel().forEach(System.out::println);
// Output: 3 1 5 2 4 (or any order)

IntStream.range(1, 6).parallel().forEachOrdered(System.out::println);
// Output: 1 2 3 4 5 (always)
```

**When to use `forEachOrdered`:** Only when order matters (e.g., writing log lines to a file in sequence). The ordering overhead often negates parallel speedup — if you need ordered output, question whether parallel is worthwhile at all.

**Production gotcha:** `System.out.println` is synchronized, so the output appears ordered by accident in some environments even with `forEach`. Don't rely on this — always use `forEachOrdered` when order matters.

---

## 4. Collectors Deep Dive

### Q14. What are the differences between `toList()`, `Collectors.toList()`, and `Collectors.toUnmodifiableList()`?

| Method | Modifiable? | Null-safe? | Java version |
|---|---|---|---|
| `Collectors.toList()` | Yes (ArrayList) | Yes (allows nulls) | Java 8 |
| `Collectors.toUnmodifiableList()` | No (throws UOE on add/remove) | No (throws NPE on null elements) | Java 10 |
| `Stream.toList()` | No (throws UOE) | No (throws NPE on null elements) | Java 16 |

```java
// Java 8 — mutable list, allows nulls
List<String> mutable = stream.collect(Collectors.toList());
mutable.add("extra"); // works

// Java 10 — unmodifiable, null-free
List<String> immutable = stream.collect(Collectors.toUnmodifiableList());
immutable.add("extra"); // UnsupportedOperationException

// Java 16 — cleanest, same behavior as toUnmodifiableList()
List<String> compact = stream.toList();
```

**Interview trap:** `Collections.unmodifiableList(Collectors.toList())` produces an *unmodifiable view* of a mutable list — someone holding the original list can still modify it. `toUnmodifiableList()` and `Stream.toList()` produce truly immutable lists.

---

### Q15. Explain `groupingBy` — single-level, multi-level, and downstream collectors.

```java
record Employee(String name, String dept, double salary) {}

List<Employee> employees = List.of(
    new Employee("Alice", "Engineering", 120_000),
    new Employee("Bob", "Engineering", 95_000),
    new Employee("Carol", "HR", 80_000),
    new Employee("Dave", "HR", 75_000)
);

// Single-level: Map<String, List<Employee>>
Map<String, List<Employee>> byDept = employees.stream()
    .collect(Collectors.groupingBy(Employee::dept));

// With downstream: Map<String, Long> (count per dept)
Map<String, Long> countByDept = employees.stream()
    .collect(Collectors.groupingBy(Employee::dept, Collectors.counting()));

// With downstream: Map<String, Double> (avg salary per dept)
Map<String, Double> avgSalaryByDept = employees.stream()
    .collect(Collectors.groupingBy(Employee::dept, 
        Collectors.averagingDouble(Employee::salary)));

// Multi-level: Map<String, Map<String, List<Employee>>>
// (group by dept, then by name length bucket)
Map<String, Map<String, List<Employee>>> nested = employees.stream()
    .collect(Collectors.groupingBy(Employee::dept,
        Collectors.groupingBy(e -> e.name().length() > 4 ? "long" : "short")));

// Highest-paid per department (FAANG favorite):
Map<String, Optional<Employee>> highestPaid = employees.stream()
    .collect(Collectors.groupingBy(Employee::dept,
        Collectors.maxBy(Comparator.comparingDouble(Employee::salary))));
```

**Common follow-up:** How do you get a `Map<String, Employee>` (not Optional) for highest paid?
```java
Map<String, Employee> highestPaid = employees.stream()
    .collect(Collectors.toMap(
        Employee::dept,
        e -> e,
        BinaryOperator.maxBy(Comparator.comparingDouble(Employee::salary))
    ));
```

---

### Q16. What is `partitioningBy` and how does it differ from `groupingBy`?

`partitioningBy` is a specialized `groupingBy` that always produces a `Map<Boolean, List<T>>` with exactly two keys: `true` and `false`.

```java
Map<Boolean, List<Employee>> partition = employees.stream()
    .collect(Collectors.partitioningBy(e -> e.salary() > 90_000));

List<Employee> highEarners = partition.get(true);
List<Employee> others = partition.get(false);
```

**Differences from `groupingBy`:**
1. Always returns exactly two entries (true/false), even if one is empty
2. Slightly more efficient (uses an internal two-element structure)
3. Predicate-based, not classifier-based
4. Can take a downstream collector: `partitioningBy(predicate, Collectors.counting())`

**When to use:** Whenever you're splitting into two groups based on a boolean condition — pass/fail, senior/junior, eligible/ineligible.

---

### Q17. How does `Collectors.toMap` work, and what causes `IllegalStateException`?

```java
// Basic: List<Employee> → Map<name, salary>
Map<String, Double> salaryMap = employees.stream()
    .collect(Collectors.toMap(Employee::name, Employee::salary));
```

**The duplicate key trap:** If two elements produce the same key, `toMap` throws `IllegalStateException: Duplicate key`. Fix with the merge function (third argument):

```java
// With merge function: keep the higher salary for duplicates
Map<String, Double> salaryMap = employees.stream()
    .collect(Collectors.toMap(
        Employee::name,
        Employee::salary,
        (existing, replacement) -> Math.max(existing, replacement) // merge
    ));
```

**Three-argument form with map factory:**
```java
// LinkedHashMap to preserve insertion order
Map<String, Double> ordered = employees.stream()
    .collect(Collectors.toMap(
        Employee::name,
        Employee::salary,
        (a, b) -> a, // keep first on conflict
        LinkedHashMap::new
    ));
```

**Null value gotcha:** `toMap` throws `NullPointerException` if any value is null. Use `Collectors.toUnmodifiableMap` or explicitly handle nulls.

---

### Q18. What is `collectingAndThen` and when do you use it?

`collectingAndThen` wraps another collector and applies a finishing function to the result:

```java
// Collect to list, then wrap in unmodifiable
List<String> immutable = stream.collect(
    Collectors.collectingAndThen(Collectors.toList(), Collections::unmodifiableList)
);

// Collect to list, get first element (or throw)
String first = stream.collect(
    Collectors.collectingAndThen(Collectors.toList(), list -> list.get(0))
);

// Count, then check if > 10
boolean hasMany = stream.collect(
    Collectors.collectingAndThen(Collectors.counting(), count -> count > 10)
);
```

**Common use:** Grouping into unmodifiable lists:
```java
Map<String, List<Employee>> byDept = employees.stream()
    .collect(Collectors.groupingBy(
        Employee::dept,
        Collectors.collectingAndThen(Collectors.toList(), Collections::unmodifiableList)
    ));
```

---

### Q19. Explain `Collectors.teeing` (Java 12) with a practical example.

`teeing` applies two downstream collectors simultaneously to the same stream, then merges their results:

```java
Collectors.teeing(downstream1, downstream2, merger)
```

```java
// Compute min and max in a single pass (without sorting or two streams)
record MinMax(int min, int max) {}

MinMax result = IntStream.of(3, 1, 4, 1, 5, 9, 2, 6)
    .boxed()
    .collect(Collectors.teeing(
        Collectors.minBy(Comparator.naturalOrder()),
        Collectors.maxBy(Comparator.naturalOrder()),
        (min, max) -> new MinMax(min.orElseThrow(), max.orElseThrow())
    ));
// MinMax(min=1, max=9)

// Compute sum and count to derive average without averaging collector
record SumCount(long sum, long count) {
    double average() { return count == 0 ? 0 : (double) sum / count; }
}

double avg = Stream.of(1, 2, 3, 4, 5)
    .collect(Collectors.teeing(
        Collectors.summingLong(Integer::longValue),
        Collectors.counting(),
        (sum, count) -> new SumCount(sum, count).average()
    )); // 3.0
```

**Why it matters:** Before `teeing`, computing two different aggregations in one pass required a custom collector. `teeing` eliminates that boilerplate.

---

### Q20. Implement a custom Collector from scratch.

A Collector has five components: `Supplier`, `Accumulator`, `Combiner`, `Finisher`, `Characteristics`.

```java
// Custom collector: word frequency map
public class WordFrequencyCollector implements 
    Collector<String, Map<String, Long>, Map<String, Long>> {

    @Override
    public Supplier<Map<String, Long>> supplier() {
        return HashMap::new; // creates the mutable container
    }

    @Override
    public BiConsumer<Map<String, Long>, String> accumulator() {
        return (map, word) -> map.merge(word, 1L, Long::sum); // adds word to container
    }

    @Override
    public BinaryOperator<Map<String, Long>> combiner() {
        // merges two containers (called in parallel streams)
        return (map1, map2) -> {
            map2.forEach((word, count) -> map1.merge(word, count, Long::sum));
            return map1;
        };
    }

    @Override
    public Function<Map<String, Long>, Map<String, Long>> finisher() {
        return Function.identity(); // no transformation — container is already the result
    }

    @Override
    public Set<Characteristics> characteristics() {
        return Set.of(Characteristics.UNORDERED); // result order doesn't matter
        // Add IDENTITY_FINISH if finisher is identity (skips finisher call)
        // Add CONCURRENT only if accumulator is thread-safe
    }
}

// Usage
Map<String, Long> freq = Stream.of("apple banana apple cherry banana apple")
    .flatMap(s -> Arrays.stream(s.split(" ")))
    .collect(new WordFrequencyCollector());
// {apple=3, banana=2, cherry=1}

// Simpler with Collector.of factory:
Collector<String, Map<String, Long>, Map<String, Long>> wordFreq = 
    Collector.of(
        HashMap::new,
        (map, word) -> map.merge(word, 1L, Long::sum),
        (map1, map2) -> { map2.forEach((k, v) -> map1.merge(k, v, Long::sum)); return map1; },
        Collector.Characteristics.UNORDERED
    );
```

---

## 5. Coding Problems

### Q21. Group employees by department, find highest-paid per department.

```java
// Approach 1: groupingBy + maxBy
Map<String, Optional<Employee>> highestPaid = employees.stream()
    .collect(Collectors.groupingBy(
        Employee::dept,
        Collectors.maxBy(Comparator.comparingDouble(Employee::salary))
    ));

// Approach 2: toMap with merge (avoids Optional wrapping)
Map<String, Employee> highestPaid = employees.stream()
    .collect(Collectors.toMap(
        Employee::dept,
        Function.identity(),
        BinaryOperator.maxBy(Comparator.comparingDouble(Employee::salary))
    ));

// Approach 3: get top-N per department (more general)
int N = 2;
Map<String, List<Employee>> topNByDept = employees.stream()
    .collect(Collectors.groupingBy(
        Employee::dept,
        Collectors.collectingAndThen(
            Collectors.toList(),
            list -> list.stream()
                .sorted(Comparator.comparingDouble(Employee::salary).reversed())
                .limit(N)
                .collect(Collectors.toList())
        )
    ));
```

---

### Q22. Flatten nested lists (list of lists → flat list).

```java
List<List<Integer>> nested = List.of(
    List.of(1, 2, 3),
    List.of(4, 5),
    List.of(6, 7, 8, 9)
);

// flatMap approach
List<Integer> flat = nested.stream()
    .flatMap(Collection::stream)
    .collect(Collectors.toList()); // [1,2,3,4,5,6,7,8,9]

// Distinct values, sorted
List<Integer> sortedUnique = nested.stream()
    .flatMap(Collection::stream)
    .distinct()
    .sorted()
    .collect(Collectors.toList());

// Sum of all nested elements
int total = nested.stream()
    .flatMapToInt(list -> list.stream().mapToInt(Integer::intValue))
    .sum(); // 45
```

---

### Q23. Count word frequency from a list of sentences.

```java
List<String> sentences = List.of(
    "the quick brown fox",
    "the fox jumped over",
    "the lazy dog"
);

Map<String, Long> freq = sentences.stream()
    .flatMap(s -> Arrays.stream(s.split("\\s+")))
    .collect(Collectors.groupingBy(Function.identity(), Collectors.counting()));
// {the=3, fox=2, quick=1, brown=1, jumped=1, over=1, lazy=1, dog=1}

// Top 3 most frequent words:
freq.entrySet().stream()
    .sorted(Map.Entry.<String, Long>comparingByValue().reversed())
    .limit(3)
    .map(Map.Entry::getKey)
    .collect(Collectors.toList()); // [the, fox, ...]
```

---

### Q24. Find duplicates in a list.

```java
List<Integer> nums = List.of(1, 2, 3, 2, 4, 3, 5, 1);

// Approach 1: groupingBy + filter (finds all duplicates with counts)
Map<Integer, Long> duplicates = nums.stream()
    .collect(Collectors.groupingBy(Function.identity(), Collectors.counting()))
    .entrySet().stream()
    .filter(e -> e.getValue() > 1)
    .collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue));
// {1=2, 2=2, 3=2}

// Approach 2: Set-based (just find which are duplicated)
Set<Integer> seen = new HashSet<>();
Set<Integer> duplicateSet = nums.stream()
    .filter(n -> !seen.add(n))
    .collect(Collectors.toSet()); // {1, 2, 3}
```

---

### Q25. Find the second-highest salary (one-liner).

```java
OptionalDouble secondHighest = employees.stream()
    .mapToDouble(Employee::salary)
    .distinct()
    .sorted()
    .skip(employees.size() - 2)  // skip all but last 2
    .findFirst();

// Cleaner with boxed:
Optional<Double> secondHighest = employees.stream()
    .map(Employee::salary)
    .distinct()
    .sorted(Comparator.reverseOrder())
    .skip(1)
    .findFirst();
```

---

### Q26. Fibonacci stream using `Stream.iterate`.

```java
// Java 8 (infinite — must use limit)
Stream.iterate(new long[]{0, 1}, f -> new long[]{f[1], f[0] + f[1]})
    .limit(10)
    .map(f -> f[0])
    .forEach(System.out::println); // 0,1,1,2,3,5,8,13,21,34

// Java 9 (finite — predicate stops the stream)
Stream.iterate(new long[]{0, 1}, f -> f[0] < 1_000_000, f -> new long[]{f[1], f[0] + f[1]})
    .map(f -> f[0])
    .collect(Collectors.toList());

// Elegant with BigInteger for arbitrary precision:
Stream.iterate(
    new BigInteger[]{BigInteger.ZERO, BigInteger.ONE},
    f -> new BigInteger[]{f[1], f[0].add(f[1])}
).limit(50).map(f -> f[0]).collect(toList());
```

---

### Q27. Running total / cumulative sum.

```java
List<Integer> values = List.of(1, 2, 3, 4, 5);

// Java 8: reduce with a list (O(n²) — for illustration only)
// WRONG for large datasets, shown for educational purposes:
List<Integer> cumsum = IntStream.range(0, values.size())
    .mapToObj(i -> values.subList(0, i + 1).stream().mapToInt(Integer::intValue).sum())
    .collect(Collectors.toList()); // [1,3,6,10,15]

// Correct O(n) approach: use an AtomicInteger as mutable accumulator
AtomicInteger runningTotal = new AtomicInteger(0);
List<Integer> cumsum = values.stream()
    .map(n -> runningTotal.addAndGet(n))
    .collect(Collectors.toList()); // [1,3,6,10,15]

// Note: AtomicInteger trick only works for sequential streams.
// For parallel, you need a different approach (prefix sum array).
```

---

### Q28. Anagram grouping.

```java
List<String> words = List.of("eat", "tea", "tan", "ate", "nat", "bat");

Map<String, List<String>> anagramGroups = words.stream()
    .collect(Collectors.groupingBy(word -> {
        char[] chars = word.toCharArray();
        Arrays.sort(chars);
        return new String(chars); // canonical key
    }));
// {aet=[eat, tea, ate], ant=[tan, nat], abt=[bat]}
```

---

## 6. Method References & Functional Interfaces

### Q29. What are the four types of method references?

```java
// 1. Static method reference: Class::staticMethod
Function<String, Integer> parse = Integer::parseInt;
parse.apply("42"); // 42

// 2. Instance method of arbitrary type: Class::instanceMethod
// The first argument becomes the receiver
Function<String, String> upper = String::toUpperCase;
upper.apply("hello"); // HELLO

BiPredicate<String, String> startsWith = String::startsWith;
startsWith.test("hello", "he"); // true

// 3. Instance method of particular object: instance::instanceMethod
String prefix = "http://";
Predicate<String> isUrl = prefix::startsWith; // wrong example — see below
// Correct:
String target = "hello world";
Predicate<String> containsTarget = target::contains;
containsTarget.test("world"); // true

// 4. Constructor reference: Class::new
Supplier<ArrayList<String>> listFactory = ArrayList::new;
Function<Integer, ArrayList<String>> sizedList = ArrayList::new;
```

**Interview trap:** `String::toLowerCase` vs `s -> s.toLowerCase()` — the method reference is for the zero-arg overload. `s -> s.toLowerCase(Locale.US)` has no equivalent method reference.

---

### Q30. When is a method reference NOT interchangeable with a lambda?

```java
// 1. When the method is overloaded and the reference is ambiguous:
// println is overloaded — compiler can't determine which println
// stream.forEach(System.out::println); // fine — infers String
// stream.mapToInt(Integer::parseInt); // fine — infers int

// 2. When you need to pass extra arguments:
// s -> s.substring(0, 3) has no equivalent method reference
// String::substring requires two args (start, end)

// 3. When you need to chain or transform:
// s -> s.trim().toLowerCase() — no single method reference exists

// 4. When you need to handle exceptions:
// checkedMethod throws IOException — lambda can wrap in try-catch,
// method reference cannot inline exception handling
```

---

### Q31. Explain `Function.andThen` vs `Function.compose`.

Both combine two functions, but in opposite orders:

```java
Function<Integer, Integer> doubleIt = x -> x * 2;
Function<Integer, Integer> addThree = x -> x + 3;

// andThen: applies THIS function first, then the argument function
// doubleIt.andThen(addThree) = addThree(doubleIt(x)) = x*2 + 3
Function<Integer, Integer> doubleThenAdd = doubleIt.andThen(addThree);
doubleThenAdd.apply(5); // (5*2)+3 = 13

// compose: applies the argument function first, then THIS function
// doubleIt.compose(addThree) = doubleIt(addThree(x)) = (x+3)*2
Function<Integer, Integer> addThenDouble = doubleIt.compose(addThree);
addThenDouble.apply(5); // (5+3)*2 = 16
```

**Mnemonic:** `f.andThen(g)` = "f, and then g" = g(f(x)). `f.compose(g)` = "f composed with g" = f(g(x)).

**`Predicate` composition:**
```java
Predicate<String> notNull = Objects::nonNull;
Predicate<String> notEmpty = s -> !s.isEmpty();
Predicate<String> valid = notNull.and(notEmpty);  // &&
Predicate<String> either = notNull.or(notEmpty);   // ||
Predicate<String> isNull = notNull.negate();        // !
```

---

## 7. Optional Deep Dive

### Q32. `orElse` vs `orElseGet` — when does it matter?

`orElse(value)` — evaluates the default value eagerly, regardless of whether the Optional is empty.
`orElseGet(supplier)` — evaluates the supplier lazily, only if the Optional is empty.

```java
// orElse always evaluates the default expression:
Optional<String> present = Optional.of("hello");
present.orElse(expensiveComputation()); // expensiveComputation ALWAYS runs

// orElseGet evaluates supplier only if empty:
present.orElseGet(() -> expensiveComputation()); // supplier NOT called
```

**When it matters:**
1. The default involves a side effect (database lookup, API call, log entry)
2. The default is computationally expensive
3. The default throws an exception (you need `orElseThrow` for that, but the concept applies)

```java
// Production example: DB lookup as fallback
User user = cache.get(userId)
    .orElseGet(() -> database.findById(userId)); // DB only hit if cache miss
```

**Rule:** Prefer `orElseGet` with a lambda whenever the default expression has any cost. Use `orElse` only for simple constant values.

---

### Q33. `map` vs `flatMap` on Optional.

`Optional.map` — transforms the value if present, wrapping the result in a new Optional.
`Optional.flatMap` — transforms the value if present, expecting the transformation to return an Optional (avoids `Optional<Optional<T>>`).

```java
Optional<String> name = Optional.of("  hello  ");

// map: wraps result in Optional automatically
Optional<String> trimmed = name.map(String::trim); // Optional["hello"]

// flatMap: use when the mapper itself returns Optional
Optional<User> user = Optional.of("user123")
    .flatMap(id -> userRepository.findById(id)); // findById returns Optional<User>
// Without flatMap: Optional.of("user123").map(userRepository::findById)
//   returns Optional<Optional<User>> — wrong!
```

**Chain example (the classic Optional chain):**
```java
String city = order
    .flatMap(Order::getCustomer)
    .flatMap(Customer::getAddress)
    .map(Address::getCity)
    .orElse("Unknown");
```

---

### Q34. `Optional.stream()` (Java 9) — converting Optional to a Stream.

```java
// Before Java 9: convert Optional to Stream manually
Optional<String> opt = Optional.of("value");
Stream<String> stream = opt.isPresent() ? Stream.of(opt.get()) : Stream.empty();

// Java 9+: built-in stream()
Stream<String> stream = opt.stream(); // Stream["value"] or empty Stream

// Practical use: filter out empty Optionals in a list
List<Optional<String>> optionals = List.of(
    Optional.of("a"), Optional.empty(), Optional.of("b"), Optional.empty()
);
List<String> values = optionals.stream()
    .flatMap(Optional::stream) // flatMap(opt -> opt.stream())
    .collect(Collectors.toList()); // ["a", "b"]
```

---

### Q35. Optional anti-patterns.

```java
// Anti-pattern 1: Optional.get() without isPresent() check
Optional<String> opt = findValue();
String value = opt.get(); // NoSuchElementException if empty — same as null dereference

// Anti-pattern 2: Optional as method parameter
void process(Optional<String> name) { ... } // BAD — callers can pass null anyway
// Correct: overload the method or use @Nullable

// Anti-pattern 3: Optional in a collection
Map<String, Optional<User>> map = new HashMap<>(); // BAD
// The empty Optional and a missing key mean the same thing — use Map.getOrDefault

// Anti-pattern 4: Checking isPresent() + get() instead of map/orElse
if (opt.isPresent()) {
    return opt.get().toUpperCase(); // verbose
}
// Better:
return opt.map(String::toUpperCase).orElse("");

// Anti-pattern 5: Serializing Optional (it's not Serializable)
class User implements Serializable {
    Optional<String> nickname; // compilation warning, serialization issue
    // Use @Nullable String nickname instead
}
```

---

## 8. Parallel Streams

### Q36. How do parallel streams work internally?

Parallel streams use the **ForkJoinPool** common pool. When you call `.parallel()`, the stream's Spliterator is recursively split via `trySplit()` until the sub-tasks are small enough to process in a single thread. Each sub-task runs in a ForkJoin worker thread, with **work stealing** ensuring idle threads pick up unfinished sub-tasks.

```
Stream.parallel()
  → Spliterator.trySplit() (recursive halving)
  → ForkJoinPool.commonPool() (default: Runtime.getRuntime().availableProcessors() - 1 worker threads)
  → Each task processes its chunk sequentially
  → Results merged bottom-up
```

**Work stealing:** When a thread finishes its task, it steals tasks from the back of another thread's deque — keeps all cores busy without a central queue bottleneck.

---

### Q37. When is parallel faster vs slower?

**Parallel wins when:**
1. Large data set (> ~10,000 elements — JMH-benchmark your specific case)
2. CPU-bound operation (not I/O bound)
3. Source is easily splittable (ArrayList, arrays, IntStream.range) — has `SIZED + SUBSIZED`
4. Operations are stateless (no shared mutable state)
5. Merging results is cheap

**Parallel loses when:**
1. Small data set — splitting/merging overhead exceeds computation savings
2. I/O bound — threads block, common pool starves, no CPU to gain
3. Source is not splittable (LinkedList, `Files.lines()` — LinkedList's `trySplit()` is O(n))
4. Stateful operations (`distinct`, `sorted`) — requires full buffering and merge
5. Output requires ordering — `forEachOrdered` serializes the merge

**Simple benchmark rule:** If the per-element operation is faster than ~100µs, parallel is unlikely to help for lists under 10k elements. Profile before assuming parallel is faster.

---

### Q38. How do you use a custom ForkJoinPool to avoid starving the common pool?

```java
// Default: uses ForkJoinPool.commonPool()
// Problem: all parallel streams in the JVM share this pool
// If one task submits many slow tasks, others starve

// Solution: custom ForkJoinPool
ForkJoinPool customPool = new ForkJoinPool(4); // 4 worker threads

Future<Long> result = customPool.submit(() ->
    LongStream.rangeClosed(1, 1_000_000)
        .parallel()
        .sum()
);

long sum = result.get();
customPool.shutdown();
```

**Production warning:** This works by exploiting the fact that ForkJoin tasks submitted to a custom pool run in that pool even if they internally create parallel streams. It's not an officially documented API contract — it works in Java 8–21 but could change. In Java 21+, virtual threads provide a better alternative for I/O-heavy workloads.

---

## 9. Stream Sources & Infinite Streams

### Q39. What are the key stream sources and their characteristics?

```java
// Finite sources
Stream.of("a", "b", "c")         // ORDERED, SIZED, IMMUTABLE
Arrays.stream(array)               // ORDERED, SIZED, IMMUTABLE
collection.stream()                // varies by collection type
IntStream.range(0, 100)            // ORDERED, SIZED, SUBSIZED, IMMUTABLE
IntStream.rangeClosed(1, 100)      // same

// Infinite sources (must be limited)
Stream.iterate(0, n -> n + 1)     // ORDERED, IMMUTABLE (no SIZED)
Stream.generate(Math::random)      // IMMUTABLE, UNORDERED (no SIZED)
new Random().ints()                // IntStream, infinite

// File-based
Files.lines(Path.of("file.txt"))  // ORDERED, must close (use try-with-resources)
BufferedReader.lines()             // ORDERED

// String splitting
Pattern.compile(",").splitAsStream("a,b,c") // ORDERED
```

**The Spliterator characteristic that matters most for performance:** `SIZED` — without it, `count()` must iterate. `ArrayList` has it; `LinkedList` doesn't.

---

### Q40. `Stream.iterate` — Java 8 vs Java 9 overload.

```java
// Java 8: infinite, requires limit()
Stream<Integer> infinite = Stream.iterate(0, n -> n + 1);
// Must use limit() or findFirst() etc. — never collect() without limit!

// Java 9: finite, predicate-based (like a while loop)
Stream<Integer> finite = Stream.iterate(0, n -> n < 100, n -> n + 1);
// Auto-stops when predicate returns false — no limit() needed

// Practical: generate powers of 2 up to 1024
Stream.iterate(1, n -> n <= 1024, n -> n * 2)
    .collect(Collectors.toList()); // [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]
```

---

### Q41. Primitive streams — why they exist and how to convert.

**Why:** Autoboxing `int → Integer` has non-trivial overhead per element. For numeric pipelines, `IntStream`, `LongStream`, `DoubleStream` avoid boxing entirely.

```java
// Boxed approach (boxing overhead per element):
List<Integer> nums = List.of(1, 2, 3, 4, 5);
int sum = nums.stream().mapToInt(Integer::intValue).sum(); // unboxes

// Native: no boxing at all
int sum = IntStream.rangeClosed(1, 5).sum();

// Conversions:
IntStream intStream = stream.mapToInt(String::length);    // Stream<T> → IntStream
Stream<Integer> boxed = intStream.boxed();                 // IntStream → Stream<Integer>
Stream<String> mapped = intStream.mapToObj(Integer::toString); // IntStream → Stream<T>

// Statistics in one pass:
IntSummaryStatistics stats = IntStream.of(1, 2, 3, 4, 5)
    .summaryStatistics();
// stats.getSum(), getMin(), getMax(), getAverage(), getCount()
```

---

## 10. Stream Gotchas & Tricky Questions

### Q42. Stream reuse — `IllegalStateException`.

```java
Stream<String> stream = List.of("a", "b", "c").stream();
stream.forEach(System.out::println); // fine

stream.forEach(System.out::println); // IllegalStateException: stream has already been operated upon or closed
```

Streams are single-use. After a terminal operation, the stream is consumed.

**Fix:** Create a new stream or store in a `Supplier<Stream<T>>`:
```java
Supplier<Stream<String>> streamSupplier = () -> list.stream();
streamSupplier.get().forEach(System.out::println); // fresh stream each time
```

---

### Q43. Modifying the source during stream operation.

```java
List<String> list = new ArrayList<>(List.of("a", "b", "c"));

// ConcurrentModificationException — modifying source during traversal:
list.stream().forEach(s -> {
    if (s.equals("b")) list.remove(s); // throws ConcurrentModificationException
});

// Fix: collect to a new list, then remove
List<String> toRemove = list.stream().filter(s -> s.equals("b")).collect(toList());
list.removeAll(toRemove);

// Or use removeIf (the correct tool):
list.removeIf(s -> s.equals("b"));
```

---

### Q44. `Collectors.toMap` with null values.

```java
Map<String, String> map = employees.stream()
    .collect(Collectors.toMap(
        Employee::name,
        e -> e.nickname() // returns null for some employees
    )); // NullPointerException — toMap doesn't allow null values

// Fix: replace null with a sentinel
.collect(Collectors.toMap(
    Employee::name,
    e -> e.nickname() != null ? e.nickname() : ""
));

// Or use HashMap with put:
Map<String, String> map = new HashMap<>();
employees.forEach(e -> map.put(e.name(), e.nickname())); // allows null values
```

---

### Q45. `distinct()` in parallel streams — the hidden cost.

`distinct()` maintains a shared `ConcurrentHashSet` across all threads in a parallel stream. Every element check requires a thread-safe lookup and potential insertion — this is a synchronized bottleneck:

```java
// Slow: distinct() in parallel serializes through a shared set
largeStream.parallel().distinct().collect(toList());

// Often faster: sequential distinct then parallel processing
largeStream.distinct().parallel().collect(toList());

// Or use a different approach:
// Collect to a Set (naturally distinct), then parallel process:
largeStream.collect(Collectors.toSet()).parallelStream().collect(toList());
```

---

## 11. Java 9–25 Stream Additions

### Q46. What stream features were added in Java 9–24?

**Java 9:**
```java
// takeWhile / dropWhile
Stream.of(1,2,3,4,5).takeWhile(n -> n < 4).collect(toList()); // [1,2,3]

// Stream.iterate with predicate
Stream.iterate(0, n -> n < 10, n -> n + 1).collect(toList());

// Stream.ofNullable — avoids null check before creating stream
Stream.ofNullable(null).count(); // 0 (empty stream, not NPE)
Stream.ofNullable("value").count(); // 1
```

**Java 12:**
```java
// Collectors.teeing — see Q19
```

**Java 16:**
```java
// Stream.toList() — unmodifiable, null-free shorthand
List<String> list = stream.toList(); // equivalent to .collect(toUnmodifiableList())

// mapMulti — see Q7
```

**Java 21+ (Sequenced Collections):**
```java
// reversed() on SequencedCollection — sorted stream in reverse without Comparator
List<String> list = new ArrayList<>(List.of("a", "b", "c"));
list.reversed().stream().forEach(System.out::println); // c, b, a
```

**Java 22–24 (`Stream.gather` + `Gatherer`):**
```java
// Custom intermediate operation via Gatherer (preview in 22, standard in 24)
// Example: sliding window of size 3
Stream.of(1,2,3,4,5)
    .gather(Gatherers.windowSliding(3))
    .forEach(System.out::println);
// [1,2,3], [2,3,4], [3,4,5]

// scan (running total using Gatherers)
Stream.of(1,2,3,4,5)
    .gather(Gatherers.scan(() -> 0, (acc, e) -> acc + e))
    .collect(toList()); // [1,3,6,10,15]
```

---

## 12. Streams vs Loops

### Q47. When should you prefer a loop over a stream?

**Prefer loops when:**
1. Early exit with complex mutable state (simpler with `break`/`continue` than stream workarounds)
2. Performance-critical inner loop on primitive arrays (`int[]`, `long[]`)
3. Multiple iterators over different collections in sync
4. Checked exceptions — lambdas don't propagate checked exceptions cleanly
5. Debugging is critical — stack traces in streams show lambda line numbers, not element values

```java
// Complex stateful exit — loop is clearer
outer:
for (int i = 0; i < matrix.length; i++) {
    for (int j = 0; j < matrix[i].length; j++) {
        if (matrix[i][j] == target) {
            result = new int[]{i, j};
            break outer;
        }
    }
}
```

**Prefer streams when:**
1. Transforming/filtering collections into a new collection
2. Aggregation (sum, count, average, group)
3. The pipeline is parallelizable (large data, CPU-bound)
4. Code reads more like a specification than an algorithm

---

### Q48. Debugging streams — `peek` pattern and common techniques.

```java
// Technique 1: peek (see Q9 for caveats)
stream.filter(x -> x > 0)
    .peek(x -> System.out.println("after filter: " + x))
    .map(x -> x * 2)
    .collect(toList());

// Technique 2: break pipeline into steps — assign intermediate to list
List<Integer> afterFilter = stream.filter(x -> x > 0).collect(toList());
// Inspect afterFilter in debugger
List<Integer> result = afterFilter.stream().map(x -> x * 2).collect(toList());

// Technique 3: IntelliJ IDEA Stream Debugger
// Set a breakpoint in any lambda — IDE shows stream steps visually

// Technique 4: logging wrapper
stream.filter(loggingPredicate("filter", x -> x > 0))
    .map(x -> x * 2)
    .collect(toList());

static <T> Predicate<T> loggingPredicate(String name, Predicate<T> p) {
    return t -> {
        boolean result = p.test(t);
        System.out.printf("[%s] %s → %s%n", name, t, result);
        return result;
    };
}
```

---

## 13. Functional Programming Concepts

### Q49. Why must lambdas use effectively final variables?

Lambdas in Java are **closures** — they capture variables from the enclosing scope. The JVM implements this by passing the captured variable as a synthetic field in the generated anonymous class.

If the variable were mutable, it could change after the lambda is created, causing the lambda to observe stale values (especially in concurrent contexts). The "effectively final" rule is a compile-time guarantee that the variable won't change.

```java
int count = 0;
stream.forEach(s -> count++); // Compile error: count must be effectively final

// Fix: use an AtomicInteger for mutable state in lambdas
AtomicInteger count = new AtomicInteger(0);
stream.forEach(s -> count.incrementAndGet()); // OK

// Or better: use reduce/collect instead of mutating external state
long count = stream.count();
```

---

### Q50. Memoization with `ConcurrentHashMap.computeIfAbsent`.

```java
// Memoize expensive computation:
Map<Integer, Long> cache = new ConcurrentHashMap<>();
Function<Integer, Long> memoFib = null;
// Can't self-reference with lambda directly — use array trick:
Function<Integer, Long>[] ref = new Function[1];
ref[0] = n -> cache.computeIfAbsent(n, k ->
    k <= 1 ? k : ref[0].apply(k - 1) + ref[0].apply(k - 2)
);

// Cleaner with a class:
class Memoizer<T, R> {
    private final Map<T, R> cache = new ConcurrentHashMap<>();
    private final Function<T, R> function;
    
    Memoizer(Function<T, R> function) { this.function = function; }
    
    R apply(T t) { return cache.computeIfAbsent(t, function); }
}

Memoizer<String, Integer> wordLength = new Memoizer<>(String::length);
wordLength.apply("hello"); // computed
wordLength.apply("hello"); // cached
```

**`computeIfAbsent` thread safety:** In `ConcurrentHashMap`, `computeIfAbsent` is atomic per key — no two threads will compute the same key simultaneously. The value function must be fast and non-blocking (it holds the segment lock).

---

### Q51. Currying and partial application in Java.

```java
// Currying: transform f(a, b) into f(a)(b)
// Java function: a → (b → result)
Function<Integer, Function<Integer, Integer>> curriedAdd = a -> b -> a + b;
curriedAdd.apply(3).apply(4); // 7

// Partial application: fix some arguments
Function<Integer, Integer> add5 = curriedAdd.apply(5);
add5.apply(3); // 8
add5.apply(10); // 15

// Practical: reusable tax calculator
BiFunction<Double, Double, Double> taxCalculator = (price, rate) -> price * (1 + rate);
Function<Double, Double> gstCalculator = price -> taxCalculator.apply(price, 0.18);
Function<Double, Double> vatCalculator = price -> taxCalculator.apply(price, 0.05);

gstCalculator.apply(1000.0); // 1180.0
vatCalculator.apply(1000.0); // 1050.0
```

---

## 14. Production Scenarios

### Q52. Memory leak: `Files.lines()` stream not closed.

```java
// WRONG: stream not closed — file handle leaked
Stream<String> lines = Files.lines(Path.of("large.log"));
long count = lines.count(); // count completes, but file handle never released

// CORRECT: use try-with-resources
try (Stream<String> lines = Files.lines(Path.of("large.log"))) {
    long errorCount = lines.filter(l -> l.contains("ERROR")).count();
}
// File handle closed regardless of exception

// Why it matters: on Linux, each JVM process has a max fd limit (~65535)
// Leaking one stream per request = file descriptor exhaustion under load
```

**`Files.lines()` vs `Files.readAllLines()`:**
- `readAllLines()` — loads entire file into a `List<String>`. Simple but OOMs on large files.
- `Files.lines()` — lazy stream, reads line by line. Memory-efficient but requires proper closure.

Rule: For files > a few MB, always use `Files.lines()` with `try-with-resources`.

---

### Q53. `Stream.of(int[])` vs `Arrays.stream(int[])`.

```java
int[] arr = {1, 2, 3};

// Stream.of(arr): creates Stream<int[]> — a stream of ONE element (the array)
Stream<int[]> wrong = Stream.of(arr);
wrong.count(); // 1 — not 3!

// Arrays.stream(arr): creates IntStream — a stream of THREE elements
IntStream correct = Arrays.stream(arr);
correct.count(); // 3

// For Integer[] (boxed), both work:
Integer[] boxed = {1, 2, 3};
Stream<Integer> s1 = Stream.of(boxed);       // Stream of 3
Stream<Integer> s2 = Arrays.stream(boxed);   // Stream of 3
```

**Rule:** For primitive arrays (`int[]`, `long[]`, `double[]`), always use `Arrays.stream()`. `Stream.of()` treats the array as a single object.

---

### Q54. Parallel stream + ThreadLocal — values not propagated.

```java
ThreadLocal<String> context = ThreadLocal.withInitial(() -> "default");
context.set("request-123");

// Sequential: same thread, ThreadLocal works
stream.sequential().forEach(e -> System.out.println(context.get())); // request-123

// Parallel: worker threads don't inherit the main thread's ThreadLocal
stream.parallel().forEach(e -> System.out.println(context.get())); // "default"!
```

**Why:** ForkJoinPool worker threads are separate threads. `ThreadLocal` is per-thread. The worker threads get the initialValue, not the main thread's set value.

**Fix:** Pass context explicitly as a captured (effectively final) variable:
```java
String ctx = context.get(); // capture before the stream
stream.parallel().forEach(e -> process(e, ctx)); // pass explicitly
```

**Production impact:** Spring's `RequestContextHolder`, MDC logging, security context in parallel streams — all behave this way. Always capture context before parallelizing.

---

## 15. Rapid-Fire Coding Round

### Q55. One-liners.

```java
// First non-repeating character
Optional<Character> first = str.chars()
    .mapToObj(c -> (char) c)
    .collect(Collectors.groupingBy(Function.identity(), LinkedHashMap::new, Collectors.counting()))
    .entrySet().stream()
    .filter(e -> e.getValue() == 1)
    .map(Map.Entry::getKey)
    .findFirst();

// Group strings by length
Map<Integer, List<String>> byLength = words.stream()
    .collect(Collectors.groupingBy(String::length));

// Merge two maps summing values for duplicate keys
Map<String, Integer> merged = Stream.of(map1, map2)
    .flatMap(m -> m.entrySet().stream())
    .collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue, Integer::sum));

// Convert List<String> to Map<String, Integer> (word → length)
Map<String, Integer> wordLengths = words.stream()
    .collect(Collectors.toMap(Function.identity(), String::length));

// Partition numbers into even/odd
Map<Boolean, List<Integer>> partition = nums.stream()
    .collect(Collectors.partitioningBy(n -> n % 2 == 0));

// Check if all elements are positive, return first negative
Optional<Integer> firstNegative = nums.stream()
    .filter(n -> n < 0)
    .findFirst();
// If empty: all positive; if present: contains first failing element

// Transpose a 2D matrix (NxM → MxN)
int[][] matrix = {{1,2,3},{4,5,6}};
int rows = matrix.length, cols = matrix[0].length;
int[][] transposed = IntStream.range(0, cols)
    .mapToObj(c -> IntStream.range(0, rows).map(r -> matrix[r][c]).toArray())
    .toArray(int[][]::new);
```

---

*Total: 55 Q&As across 15 sections.*
*Focus areas by company: Collectors (Amazon/Flipkart), Parallel (Google/Goldman), Optional (JP Morgan), Gotchas (Uber/Atlassian), Functional Patterns (Razorpay/Atlassian).*
