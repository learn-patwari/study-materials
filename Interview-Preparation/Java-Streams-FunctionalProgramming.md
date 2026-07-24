# Java Streams & Functional Programming — Senior Interview Q&A (10–15 YOE)

> Target: Engineers with 10–15 years experience. No basic definitions — every answer covers internals, gotchas, and production relevance.
> Companies: Google, Amazon, JP Morgan, Goldman Sachs, Uber, Flipkart, Atlassian, Razorpay

---

## Table of Contents

1. [Stream Pipeline Internals](#1-stream-pipeline-internals)
2. [Intermediate Operations Deep Dive](#2-intermediate-operations-deep-dive)
3. [Terminal Operations & Short-Circuiting](#3-terminal-operations--short-circuiting)
4. [Collectors Deep Dive](#4-collectors-deep-dive)
5. [Custom Collector Implementation](#5-custom-collector-implementation)
6. [Method References & Functional Interfaces](#6-method-references--functional-interfaces)
7. [Optional Deep Dive](#7-optional-deep-dive)
8. [Parallel Streams](#8-parallel-streams)
9. [Infinite Streams & Stream Sources](#9-infinite-streams--stream-sources)
10. [Stream Gotchas & Tricky Questions](#10-stream-gotchas--tricky-questions)
11. [Java 9–25 Stream Additions](#11-java-925-stream-additions)
12. [Streams vs Loops — Production Decisions](#12-streams-vs-loops--production-decisions)
13. [Functional Programming Concepts](#13-functional-programming-concepts)
14. [Coding Problems (Most Asked)](#14-coding-problems-most-asked)
15. [Production Scenarios & Debugging](#15-production-scenarios--debugging)
16. [Rapid-Fire Round](#16-rapid-fire-round)

---

## 1. Stream Pipeline Internals

### Q1. Explain how a Stream pipeline actually executes — what happens between `stream()` and the terminal operation?

**The critical point most candidates miss**: calling intermediate operations like `filter()` or `map()` does **nothing**. They return a new `Stream` object that wraps the previous stage in a linked chain. No data flows until you call a terminal operation.

Internally, each intermediate op creates a `StatelessOp` or `StatefulOp` node chained into a `ReferencePipeline`. When the terminal operation is called:

1. A `Sink` chain is built — each stage gets a `Sink<T>` that knows how to push elements to the next stage
2. The source's `Spliterator` starts feeding elements one by one into the head `Sink`
3. Each element travels the **entire pipeline** before the next element is pulled

```
Source → filter(Sink) → map(Sink) → collect(Sink)
         ↑ element 1 travels all the way before element 2 starts
```

This is **vertical execution** (element-by-element) not **horizontal execution** (stage-by-stage).

```java
List<String> result = List.of("a", "bb", "ccc", "d")
    .stream()
    .peek(s -> System.out.println("filter input: " + s))
    .filter(s -> s.length() > 1)
    .peek(s -> System.out.println("map input: " + s))
    .map(String::toUpperCase)
    .collect(Collectors.toList());

// Output:
// filter input: a      ← a fails filter, never reaches map
// filter input: bb
// map input: bb        ← bb passes, goes to map immediately
// filter input: ccc
// map input: ccc
// filter input: d      ← d fails, never reaches map
```

**Consequence**: A `limit(1)` after a `filter` stops pulling elements the moment one passes the filter — it does NOT process all elements then take the first.

**Spliterator**: The source of elements. `Collection.stream()` creates a `Spliterator` via `spliterator()`. Its characteristics (ORDERED, SIZED, DISTINCT, SORTED, IMMUTABLE, CONCURRENT, SUBSIZED) tell the stream engine what optimizations are safe.

---

### Q2. How many passes does a stream pipeline make over the data?

**One pass.** The pipeline is fused — element-by-element vertical execution means a single traversal regardless of how many intermediate operations you chain.

Exception: **stateful operations** (`sorted()`, `distinct()`, `limit()`). `sorted()` must buffer all elements before emitting any. `distinct()` maintains a seen-set. Each stateful op can introduce a barrier where elements accumulate before the next stage fires.

```java
// This requires buffering ALL elements for sort, THEN one pass for map
stream.sorted().map(f)

// vs this — single fused pass, map happens per element as filter passes
stream.filter(p).map(f)
```

---

### Q3. What is a Spliterator and why does it matter for parallel streams?

`Spliterator<T>` (splittable iterator) is the source abstraction for streams. It has two key methods:
- `tryAdvance(Consumer)` — process one element
- `trySplit()` — split into two Spliterators (enables parallelism)

The `trySplit()` method is what parallel streams call recursively to partition work across ForkJoin threads. If `trySplit()` returns null (can't split), that source is processed serially even in a parallel stream.

**Characteristics** matter for optimization:
- `SIZED`: total count is known → parallel can split evenly
- `ORDERED`: elements have encounter order → parallel must preserve it (costs performance)
- `IMMUTABLE`/`CONCURRENT`: source won't change → no CME risk

`ArrayList` has an efficient `Spliterator` (index-based splitting). `LinkedList`'s is poor (must traverse to midpoint). This is why `ArrayList` parallelizes well but `LinkedList` doesn't.

---

## 2. Intermediate Operations Deep Dive

### Q4. What is the difference between `map` and `flatMap`? When does flatMap perform better?

`map` applies a 1-to-1 function: one input → one output.
`flatMap` applies a 1-to-many function then flattens: one input → a `Stream` of outputs → elements merged into one stream.

```java
List<List<Integer>> nested = List.of(List.of(1,2), List.of(3,4), List.of(5));

// map gives Stream<List<Integer>> — still nested
nested.stream().map(List::stream);    // Stream<Stream<Integer>>

// flatMap gives Stream<Integer> — flattened
nested.stream().flatMap(List::stream) // Stream<Integer>: 1,2,3,4,5
     .collect(Collectors.toList());   // [1, 2, 3, 4, 5]
```

**Real-world example** — extract all order items across all orders:
```java
List<String> allItems = orders.stream()
    .flatMap(order -> order.getItems().stream())
    .distinct()
    .collect(Collectors.toList());
```

**`mapMulti` (Java 16) vs `flatMap`**: `flatMap` creates a new `Stream` object per element (heap allocation per element). `mapMulti` uses a consumer-push model — no intermediate stream object created. For large datasets with many small outputs, `mapMulti` can be meaningfully faster:

```java
// flatMap — creates a new Stream for each element
stream.flatMap(s -> Stream.of(s.toLowerCase(), s.toUpperCase()))

// mapMulti — pushes directly into downstream, no intermediate Stream
stream.<String>mapMulti((s, consumer) -> {
    consumer.accept(s.toLowerCase());
    consumer.accept(s.toUpperCase());
})
```

---

### Q5. Explain stateless vs stateful intermediate operations and why the distinction matters.

**Stateless**: `filter`, `map`, `flatMap`, `peek`, `mapToInt`, `mapMulti` — each element is processed independently with no knowledge of other elements. Can be fused freely, safe in parallel.

**Stateful**: `distinct`, `sorted`, `limit`, `skip` — require knowledge of other elements (seen-set, full buffer, count). They act as barriers in the pipeline.

In parallel streams, stateful ops are expensive:
- `distinct()` requires a concurrent seen-set shared across all threads
- `sorted()` must gather all elements from all threads before sorting
- `limit(n)` with unordered stream is cheap; with ordered stream forces coordination

```java
// This runs in parallel but sorted() forces full element collection first
list.parallelStream()
    .filter(x -> x > 0)
    .sorted()          // BARRIER — collects all, sorts, then continues
    .limit(10)
    .collect(toList());

// Better for top-N: avoid sorted in parallel, use a different approach
list.parallelStream()
    .filter(x -> x > 0)
    .collect(Collectors.toList())
    .stream()          // back to sequential for stateful ops
    .sorted()
    .limit(10)
    .collect(toList());
```

---

### Q6. `takeWhile` and `dropWhile` (Java 9) — how do they behave on unordered streams?

`takeWhile(predicate)`: takes elements while predicate is true, stops at first false.
`dropWhile(predicate)`: drops elements while predicate is true, passes remainder.

```java
// Ordered stream — predictable
Stream.of(1, 2, 3, 4, 5, 1, 2)
    .takeWhile(n -> n < 4)
    .forEach(System.out::println); // 1, 2, 3

Stream.of(1, 2, 3, 4, 5)
    .dropWhile(n -> n < 3)
    .forEach(System.out::println); // 3, 4, 5
```

**Unordered streams**: the behavior is non-deterministic. The stream may take/drop an arbitrary subset of elements that satisfy the predicate. This is by spec — don't use these on sets or parallel streams without ordering guarantee.

**Use case**: Processing log lines sorted by time, take entries within a time window, or drop header lines:
```java
Files.lines(path)
    .dropWhile(line -> line.startsWith("#"))   // skip comments at top
    .takeWhile(line -> !line.isEmpty())         // stop at blank line
    .forEach(processor::process);
```

---

## 3. Terminal Operations & Short-Circuiting

### Q7. Which terminal operations short-circuit and what does that mean for infinite streams?

Short-circuit terminal operations stop pulling elements once they have enough information:

| Operation | Short-circuits when |
|---|---|
| `findFirst()` | First element found |
| `findAny()` | Any element found (non-deterministic in parallel) |
| `anyMatch(p)` | First element matching p found |
| `allMatch(p)` | First element NOT matching p found |
| `noneMatch(p)` | First element matching p found |
| `limit(n)` (intermediate) | n elements passed |

Non-short-circuit: `count`, `collect`, `reduce`, `forEach`, `toArray`, `min`, `max`.

**Infinite stream pattern** — only valid with short-circuit terminal:
```java
// Find first prime > 1000
OptionalInt firstPrime = IntStream.iterate(1001, n -> n + 2)
    .filter(Java8Streams::isPrime)
    .findFirst();  // short-circuits, doesn't iterate forever

// This would hang forever:
// IntStream.iterate(0, n -> n + 1).count(); // no short-circuit
```

---

### Q8. Explain `reduce` — identity vs no-identity form, and why the combiner matters in parallel.

`reduce` has three overloads:

```java
// 1. Identity + accumulator → T (always returns a value)
T reduce(T identity, BinaryOperator<T> accumulator)

// 2. No identity → Optional<T> (empty if stream is empty)
Optional<T> reduce(BinaryOperator<T> accumulator)

// 3. Identity + accumulator + combiner → U (for type transformation in parallel)
<U> U reduce(U identity, BiFunction<U,T,U> accumulator, BinaryOperator<U> combiner)
```

**Identity contract**: the identity value must satisfy `identity op x = x` for ALL x. Violating this produces wrong results in parallel:
```java
// WRONG — 0 is not identity for multiplication
// In parallel, each partition starts with 0, then combined with *
// Result: 0 (every partition multiplied by 0 base gives wrong answer)
list.parallelStream().reduce(0, (a, b) -> a * b);  // WRONG

// CORRECT
list.parallelStream().reduce(1, (a, b) -> a * b);  // 1 is identity for *
```

**Combiner in overload 3** — needed when accumulator type differs from element type:
```java
// Sum lengths of strings: element is String, accumulator is Integer
int totalLength = Stream.of("hello", "world", "java")
    .reduce(
        0,                              // identity
        (sum, str) -> sum + str.length(), // accumulator: Integer + String -> Integer
        Integer::sum                    // combiner: Integer + Integer -> Integer (parallel merge)
    );
```

**Why `reduce` with mutable container is wrong**:
```java
// WRONG — don't use reduce to build a list
List<Integer> list = stream.reduce(new ArrayList<>(), (l, e) -> {
    l.add(e); return l;
}, (l1, l2) -> { l1.addAll(l2); return l1; });
// In parallel, identity ArrayList is SHARED across threads → race condition

// CORRECT — use collect for mutable reduction
List<Integer> list = stream.collect(Collectors.toList());
```

---

## 4. Collectors Deep Dive

### Q9. Explain `groupingBy` internals, multi-level grouping, and downstream collectors. What does the classifier function return?

`Collectors.groupingBy(classifier)` produces `Map<K, List<T>>` by default. Each element is classified into a key; elements with the same key go into the same list.

```java
// Basic grouping
Map<String, List<Employee>> byDept =
    employees.stream()
        .collect(Collectors.groupingBy(Employee::getDepartment));

// Multi-level (nested) grouping
Map<String, Map<String, List<Employee>>> byDeptAndCity =
    employees.stream()
        .collect(Collectors.groupingBy(
            Employee::getDepartment,
            Collectors.groupingBy(Employee::getCity)
        ));

// Downstream collector — count per department
Map<String, Long> countByDept =
    employees.stream()
        .collect(Collectors.groupingBy(
            Employee::getDepartment,
            Collectors.counting()
        ));

// Downstream — average salary per department
Map<String, Double> avgSalaryByDept =
    employees.stream()
        .collect(Collectors.groupingBy(
            Employee::getDepartment,
            Collectors.averagingDouble(Employee::getSalary)
        ));

// Downstream — highest paid per department
Map<String, Optional<Employee>> highestPaidByDept =
    employees.stream()
        .collect(Collectors.groupingBy(
            Employee::getDepartment,
            Collectors.maxBy(Comparator.comparingDouble(Employee::getSalary))
        ));

// Downstream — list of names per department (not full objects)
Map<String, List<String>> namesByDept =
    employees.stream()
        .collect(Collectors.groupingBy(
            Employee::getDepartment,
            Collectors.mapping(Employee::getName, Collectors.toList())
        ));
```

**Multi-level with statistics** — what Goldman Sachs / JP Morgan ask:
```java
// Per department: sum of salaries and count
Map<String, DoubleSummaryStatistics> statsByDept =
    employees.stream()
        .collect(Collectors.groupingBy(
            Employee::getDepartment,
            Collectors.summarizingDouble(Employee::getSalary)
        ));
statsByDept.forEach((dept, stats) ->
    System.out.printf("%s: avg=%.2f, max=%.2f, count=%d%n",
        dept, stats.getAverage(), stats.getMax(), stats.getCount()));
```

---

### Q10. `Collectors.toMap` — what happens with duplicate keys? How do you handle it?

Without a merge function, duplicate keys throw `IllegalStateException: Duplicate key`.

```java
// THROWS if two employees have same name
Map<String, Employee> byName = employees.stream()
    .collect(Collectors.toMap(Employee::getName, e -> e));

// With merge function — keep last occurrence
Map<String, Employee> byName = employees.stream()
    .collect(Collectors.toMap(
        Employee::getName,
        e -> e,
        (existing, replacement) -> replacement  // merge: keep newer
    ));

// With merge function — concatenate values
Map<String, String> deptToNames = employees.stream()
    .collect(Collectors.toMap(
        Employee::getDepartment,
        Employee::getName,
        (n1, n2) -> n1 + ", " + n2  // merge duplicate dept entries
    ));

// With custom map implementation (LinkedHashMap to preserve order)
Map<String, Employee> byName = employees.stream()
    .collect(Collectors.toMap(
        Employee::getName,
        e -> e,
        (e1, e2) -> e1,
        LinkedHashMap::new
    ));
```

**Null value trap**: `toMap` throws `NullPointerException` if any value is null — unlike `groupingBy` which tolerates it. Workaround: `Collectors.toUnmodifiableMap` has the same issue. Use `HashMap::new` + explicit put in a `collect` with custom downstream if nulls are possible.

---

### Q11. Explain `Collectors.teeing` (Java 12). Give a practical example.

`teeing(downstream1, downstream2, merger)` feeds each element into **two** downstream collectors simultaneously, then merges their results. Avoids two passes over the data.

```java
// Find min and max in a single pass (instead of two separate stream operations)
record MinMax(Optional<Integer> min, Optional<Integer> max) {}

MinMax result = Stream.of(3, 1, 4, 1, 5, 9, 2, 6)
    .collect(Collectors.teeing(
        Collectors.minBy(Integer::compareTo),
        Collectors.maxBy(Integer::compareTo),
        MinMax::new
    ));

// Average and count simultaneously
record Stats(Double average, Long count) {}
Stats stats = employees.stream()
    .collect(Collectors.teeing(
        Collectors.averagingDouble(Employee::getSalary),
        Collectors.counting(),
        Stats::new
    ));

// Partition into two groups and return both
record Partition<T>(List<T> matching, List<T> notMatching) {}
Partition<Employee> partition = employees.stream()
    .collect(Collectors.teeing(
        Collectors.filtering(e -> e.getSalary() > 100_000, Collectors.toList()),
        Collectors.filtering(e -> e.getSalary() <= 100_000, Collectors.toList()),
        Partition::new
    ));
```

---

### Q12. `collectingAndThen` vs wrapping in a `map` call — when do you need it?

`collectingAndThen(downstream, finisher)` applies a transformation to the **result** of the downstream collector. Essential when the downstream collector's result type needs post-processing.

```java
// Make result unmodifiable after grouping
Map<String, List<Employee>> unmodifiable = employees.stream()
    .collect(Collectors.collectingAndThen(
        Collectors.groupingBy(Employee::getDepartment),
        Collections::unmodifiableMap
    ));

// Convert list to array
String[] names = employees.stream()
    .map(Employee::getName)
    .collect(Collectors.collectingAndThen(
        Collectors.toList(),
        list -> list.toArray(String[]::new)
    ));

// Get single result (throws if multiple match)
Employee ceo = employees.stream()
    .filter(e -> e.getTitle().equals("CEO"))
    .collect(Collectors.collectingAndThen(
        Collectors.toList(),
        list -> {
            if (list.size() != 1) throw new IllegalStateException("Expected exactly one CEO");
            return list.get(0);
        }
    ));
```

---

## 5. Custom Collector Implementation

### Q13. Implement a custom `Collector` from scratch. Walk through the four components.

A `Collector<T, A, R>` has:
- `T`: input element type
- `A`: accumulator (mutable intermediate container)
- `R`: result type

Four functions + one set of characteristics:

```java
// Custom Collector: frequency map (String → count)
public class FrequencyCollector
    implements Collector<String, Map<String, Long>, Map<String, Long>> {

    @Override
    public Supplier<Map<String, Long>> supplier() {
        // Creates a new empty accumulator for each thread (or the single thread)
        return HashMap::new;
    }

    @Override
    public BiConsumer<Map<String, Long>, String> accumulator() {
        // Folds one element into the accumulator
        return (map, word) -> map.merge(word, 1L, Long::sum);
    }

    @Override
    public BinaryOperator<Map<String, Long>> combiner() {
        // Merges two partial accumulators (called in parallel streams)
        return (map1, map2) -> {
            map2.forEach((k, v) -> map1.merge(k, v, Long::sum));
            return map1;
        };
    }

    @Override
    public Function<Map<String, Long>, Map<String, Long>> finisher() {
        // Transforms accumulator to final result (identity here)
        return Function.identity();
    }

    @Override
    public Set<Characteristics> characteristics() {
        // UNORDERED: result doesn't depend on encounter order
        // IDENTITY_FINISH: finisher is identity, can be elided
        // (No CONCURRENT — HashMap is not thread-safe)
        return Set.of(Characteristics.UNORDERED, Characteristics.IDENTITY_FINISH);
    }
}

// Usage
Map<String, Long> freq = Stream.of("apple", "banana", "apple", "cherry", "banana", "apple")
    .collect(new FrequencyCollector());
// {apple=3, banana=2, cherry=1}

// Equivalent using built-in (for reference):
Map<String, Long> freq2 = stream.collect(
    Collectors.groupingBy(Function.identity(), Collectors.counting()));
```

**Characteristics explained**:
- `CONCURRENT`: accumulator can be called from multiple threads simultaneously on the same container (enables true concurrent collection, rarely needed)
- `UNORDERED`: encounter order doesn't matter for correctness
- `IDENTITY_FINISH`: finisher is `Function.identity()`, JVM can skip calling it

---

### Q14. Implement a `Collector` that returns the top N elements by a comparator.

```java
public class TopNCollector<T> implements Collector<T, PriorityQueue<T>, List<T>> {
    private final int n;
    private final Comparator<T> comparator;

    public TopNCollector(int n, Comparator<T> comparator) {
        this.n = n;
        this.comparator = comparator;
    }

    @Override
    public Supplier<PriorityQueue<T>> supplier() {
        // Min-heap of size n: smallest of the top-N is at root, evicted when full
        return () -> new PriorityQueue<>(n, comparator);
    }

    @Override
    public BiConsumer<PriorityQueue<T>, T> accumulator() {
        return (heap, element) -> {
            if (heap.size() < n) {
                heap.offer(element);
            } else if (comparator.compare(element, heap.peek()) > 0) {
                heap.poll();
                heap.offer(element);
            }
        };
    }

    @Override
    public BinaryOperator<PriorityQueue<T>> combiner() {
        return (h1, h2) -> {
            h2.forEach(e -> accumulator().accept(h1, e));
            return h1;
        };
    }

    @Override
    public Function<PriorityQueue<T>, List<T>> finisher() {
        return heap -> {
            List<T> result = new ArrayList<>(heap);
            result.sort(comparator.reversed());
            return result;
        };
    }

    @Override
    public Set<Characteristics> characteristics() {
        return Set.of(Characteristics.UNORDERED);
    }

    public static <T> Collector<T, ?, List<T>> of(int n, Comparator<T> comparator) {
        return new TopNCollector<>(n, comparator);
    }
}

// Usage: top 3 highest-paid employees
List<Employee> top3 = employees.stream()
    .collect(TopNCollector.of(3, Comparator.comparingDouble(Employee::getSalary)));
```

---

## 6. Method References & Functional Interfaces

### Q15. What are the four types of method references? When can they NOT replace a lambda?

```java
// 1. Static method reference
Function<String, Integer> parser = Integer::parseInt;
// Equivalent lambda: s -> Integer.parseInt(s)

// 2. Instance method of a particular object
String prefix = "Hello";
Predicate<String> startsWithHello = prefix::startsWith;
// Equivalent: s -> prefix.startsWith(s)

// 3. Instance method of an arbitrary object of a particular type
Function<String, String> upperCase = String::toUpperCase;
// Equivalent: s -> s.toUpperCase()
// The first parameter becomes the receiver

// 4. Constructor reference
Supplier<ArrayList<String>> listMaker = ArrayList::new;
Function<Integer, ArrayList<String>> listWithCapacity = ArrayList::new;
// JVM picks the right constructor based on the functional interface signature
```

**When method reference CANNOT replace a lambda**:

```java
// 1. When you need to adapt parameters
// String::compareTo has signature (String, String) -> int
// But you need (String, String) -> int with reversed args
Comparator<String> reversed = (a, b) -> b.compareTo(a);  // can't use method ref

// 2. When you need to pass extra arguments
list.stream().filter(s -> s.startsWith("prefix"))  // can't do String::startsWith here
// because startsWith("prefix") needs the captured arg

// 3. When the method throws a checked exception not in the functional interface
// You need a try-catch wrapper:
stream.map(s -> {
    try { return new URL(s); }
    catch (MalformedURLException e) { throw new RuntimeException(e); }
});

// 4. Ambiguous overloads
// println is overloaded — compiler can't determine which overload
// System.out::println works because the type is inferred from stream context
```

---

### Q16. Explain `Function.compose` vs `Function.andThen`. What is the difference?

Both combine two functions. The difference is **order of application**:

```java
Function<Integer, Integer> doubleIt = x -> x * 2;
Function<Integer, Integer> addTen = x -> x + 10;

// andThen: apply THIS first, then OTHER
// doubleIt.andThen(addTen) = x -> addTen(doubleIt(x)) = x -> (x*2)+10
Function<Integer, Integer> doubleThenAdd = doubleIt.andThen(addTen);
doubleThenAdd.apply(5); // (5*2)+10 = 20

// compose: apply OTHER first, then THIS
// doubleIt.compose(addTen) = x -> doubleIt(addTen(x)) = x -> (x+10)*2
Function<Integer, Integer> addThenDouble = doubleIt.compose(addTen);
addThenDouble.apply(5); // (5+10)*2 = 30
```

**Predicate composition**:
```java
Predicate<String> notEmpty = Predicate.not(String::isEmpty);   // Java 11
Predicate<String> longEnough = s -> s.length() > 5;

Predicate<String> valid = notEmpty.and(longEnough);            // both must be true
Predicate<String> either = notEmpty.or(longEnough);            // at least one true
Predicate<String> invalid = valid.negate();                    // flip result

List<String> validStrings = strings.stream()
    .filter(notEmpty.and(longEnough))
    .collect(Collectors.toList());
```

---

## 7. Optional Deep Dive

### Q17. `orElse` vs `orElseGet` — when is `orElseGet` strictly necessary?

`orElse(T value)` — the value is **always evaluated** regardless of whether Optional is present.
`orElseGet(Supplier<T>)` — the supplier is called **only when Optional is empty**.

```java
// orElse evaluates the default expression ALWAYS
Optional<User> user = findUser(id);
User result = user.orElse(createExpensiveDefaultUser()); // createExpensiveDefaultUser() ALWAYS called

// orElseGet is lazy — supplier called only when empty
User result = user.orElseGet(() -> createExpensiveDefaultUser()); // only called if empty
```

**When it matters**:
1. Default is expensive (DB call, network request, file read)
2. Default has side effects (logging, metrics, counter increment)
3. Default might throw (exception not thrown if Optional is present with `orElseGet`)

```java
// This logs every time, even when user IS present
Optional<User> user = findUser(id)
    .orElse(logAndReturnGuest()); // BAD

// This only logs when user is absent
Optional<User> user = findUser(id)
    .orElseGet(() -> logAndReturnGuest()); // GOOD
```

---

### Q18. `Optional.map` vs `Optional.flatMap` — when do you need `flatMap`?

`map(f)`: applies f, wraps result in Optional. If f returns an Optional, you get `Optional<Optional<T>>`.
`flatMap(f)`: applies f (which must return Optional), flattens the result.

```java
// User → Optional<Address> → Optional<String>
class User {
    Optional<Address> getAddress() { ... }
}
class Address {
    Optional<String> getCity() { ... }
}

// map creates nested Optional
Optional<Optional<Address>> wrong = optUser.map(User::getAddress);

// flatMap flattens
Optional<Address> address = optUser.flatMap(User::getAddress);
Optional<String> city = optUser
    .flatMap(User::getAddress)
    .flatMap(Address::getCity);

// With map for non-Optional returning methods
Optional<String> name = optUser.map(User::getName);  // getName() returns String, not Optional
```

---

### Q19. What are the Optional anti-patterns? (Asked at Amazon, Google)

```java
// ANTI-PATTERN 1: Optional.get() without isPresent() check
Optional<User> user = findUser(id);
user.get(); // NoSuchElementException if empty — defeats the purpose

// ANTI-PATTERN 2: Optional as method/constructor parameter
void sendEmail(Optional<String> email) { ... } // BAD
// Forces callers to wrap in Optional; use @Nullable or overloading instead

// ANTI-PATTERN 3: Optional in collections
Map<String, Optional<User>> cache; // BAD — use null or a sentinel value

// ANTI-PATTERN 4: Optional for primitives without OptionalInt/OptionalLong/OptionalDouble
Optional<Integer> count = ...; // BAD — boxing overhead
OptionalInt count = ...;       // GOOD

// ANTI-PATTERN 5: isPresent() + get() pattern — exactly what ifPresent/map is for
if (opt.isPresent()) { process(opt.get()); } // BAD
opt.ifPresent(this::process);                 // GOOD

// ANTI-PATTERN 6: orElse(null) — just use nullable reference at that point
User user = optUser.orElse(null); // defeats purpose; just return null from findUser

// CORRECT PATTERNS:
optUser.map(User::getEmail)
       .filter(email -> email.contains("@"))
       .ifPresent(emailService::send);

optUser.orElseThrow(() -> new UserNotFoundException(id));

// Java 9+: ifPresentOrElse
optUser.ifPresentOrElse(
    user -> log.info("Found: {}", user.getName()),
    () -> log.warn("User {} not found", id)
);
```

---

## 8. Parallel Streams

### Q20. How do parallel streams work internally? When are they slower than sequential?

Parallel streams use the **ForkJoin common pool** (`ForkJoinPool.commonPool()`). The flow:

1. `parallelStream()` creates a parallel pipeline
2. Terminal operation triggers splitting: `Spliterator.trySplit()` called recursively until threshold
3. Each sub-task submitted to ForkJoin common pool (default: CPU cores - 1 threads)
4. Results combined via the combiner functions (reduce, collect)

**When parallel is FASTER**:
- Large dataset (> 10,000 elements as rough heuristic)
- CPU-bound per-element work (not I/O)
- Easily splittable source (ArrayList, arrays — not LinkedList, Stream.iterate)
- Unordered operation (no ORDERED constraint to maintain)

**When parallel is SLOWER**:
- Small datasets — thread coordination overhead exceeds savings
- I/O-bound work — threads block on I/O, common pool exhausted, other parallel streams starve
- `sorted()` or `distinct()` in pipeline — forces full gather, negates parallel benefit
- Source can't split efficiently (LinkedList, generator-based streams)
- Object boxing overhead (use IntStream/LongStream for primitives)

```java
// WRONG — I/O in parallel stream starves common pool
list.parallelStream()
    .map(url -> httpClient.fetch(url))  // blocking I/O on common pool thread!
    .collect(toList());

// RIGHT — use CompletableFuture with dedicated executor for I/O
ExecutorService io = Executors.newFixedThreadPool(20);
List<CompletableFuture<String>> futures = list.stream()
    .map(url -> CompletableFuture.supplyAsync(() -> httpClient.fetch(url), io))
    .collect(toList());
List<String> results = futures.stream()
    .map(CompletableFuture::join)
    .collect(toList());
```

---

### Q21. How do you use a custom ForkJoinPool for parallel streams? Why would you need one?

The common pool is shared by ALL parallel streams in the JVM (including frameworks like Spring). If you run an expensive parallel operation, you starve all other parallel tasks.

```java
// Run parallel stream in a custom pool
ForkJoinPool customPool = new ForkJoinPool(4);
try {
    List<Result> results = customPool.submit(() ->
        largeList.parallelStream()
            .map(this::expensiveOperation)
            .collect(Collectors.toList())
    ).get();
} finally {
    customPool.shutdown();
}
```

**Why this works**: `ForkJoinPool.submit()` sets the pool for the duration of that task. Parallel stream tasks submitted from within that task run in the custom pool, not the common pool.

**Caveat**: This is an implementation detail, not guaranteed by the spec. Works in current OpenJDK but could change. For production, prefer `CompletableFuture` with explicit executor.

---

### Q22. `findFirst` vs `findAny` — when does the distinction matter?

Both return an Optional with one matching element.

`findFirst()` always returns the **first element in encounter order**. In parallel, this requires thread coordination to determine which element comes first — expensive for large datasets.

`findAny()` returns **any** element — whichever thread finds one first. In sequential streams it behaves like `findFirst()`. In parallel, it's faster because no coordination is needed.

```java
// Sequential — both behave identically
list.stream().filter(p).findFirst();   // first match
list.stream().filter(p).findAny();     // also first match (sequential = deterministic)

// Parallel — findAny is faster but non-deterministic
list.parallelStream().filter(p).findFirst();  // guaranteed first in encounter order (slow)
list.parallelStream().filter(p).findAny();    // any match (fast, non-deterministic)
```

Rule of thumb: if you need a specific element (e.g., lowest ID), use `findFirst` with a sorted stream or `min()`. If you just need "any one that matches" (e.g., any available server), use `findAny()` in parallel.

---

## 9. Infinite Streams & Stream Sources

### Q23. How do you create and safely consume infinite streams?

```java
// Stream.iterate — Java 8: infinite, must be limited externally
Stream.iterate(0, n -> n + 1)
    .limit(10)
    .forEach(System.out::println); // 0..9

// Stream.iterate — Java 9: predicate-bounded (finite by nature)
Stream.iterate(0, n -> n < 100, n -> n + 1)  // like a for-loop
    .forEach(System.out::println);            // 0..99

// Stream.generate — infinite from Supplier
Stream.generate(Math::random)
    .limit(5)
    .forEach(System.out::println);

// IntStream.range / rangeClosed (finite)
IntStream.range(0, 10)        // 0..9 (exclusive end)
IntStream.rangeClosed(1, 10)  // 1..10 (inclusive end)

// Fibonacci with iterate
Stream.iterate(new long[]{0, 1}, f -> new long[]{f[1], f[0] + f[1]})
    .limit(20)
    .mapToLong(f -> f[0])
    .forEach(System.out::println);

// Primes — infinite stream with filter
LongStream.iterate(2, n -> n + 1)
    .filter(this::isPrime)
    .limit(100)
    .forEach(System.out::println);
```

**Safety rules for infinite streams**:
1. Always pair with a short-circuit terminal (`findFirst`, `anyMatch`) or `limit()`
2. Never call `count()`, `collect()`, `sorted()`, `distinct()` on infinite streams
3. `Stream.generate` with stateful Supplier is not safe in parallel (shared state)

---

### Q24. Primitive streams — why do they exist and what do you lose by using `Stream<Integer>`?

`IntStream`, `LongStream`, `DoubleStream` avoid the boxing/unboxing cost of `Stream<Integer>`, `Stream<Long>`, `Stream<Double>`.

```java
// Stream<Integer> — boxes every int: 100k ints = 100k Integer objects on heap
Stream.of(1, 2, 3, 4, 5).mapToInt(Integer::intValue).sum();

// IntStream — no boxing, stack-allocated int values
IntStream.of(1, 2, 3, 4, 5).sum();
IntStream.range(1, 1_000_001).sum();  // 0 heap allocations for elements

// Converting between object and primitive streams
IntStream intStream = list.stream().mapToInt(Integer::intValue);
Stream<Integer> boxed = intStream.boxed();     // back to Stream<Integer>
Stream<Integer> boxed2 = intStream.mapToObj(Integer::valueOf);
```

**Primitive streams have extra terminal ops not available on `Stream<T>`**:
```java
IntStream.range(1, 11).sum();       // sum — not on Stream<Integer>
IntStream.range(1, 11).average();   // OptionalDouble
IntStream.range(1, 11).min();       // OptionalInt
IntStream.range(1, 11).max();       // OptionalInt
IntStream.range(1, 11).summaryStatistics(); // IntSummaryStatistics

// Conversion convenience
int[] array = IntStream.range(1, 6).toArray();
```

---

## 10. Stream Gotchas & Tricky Questions

### Q25. What happens when you reuse a stream? How does the error manifest?

Streams are **single-use**. After a terminal operation is called (or even if an intermediate operation connects the pipeline to another consumer), the stream is considered operated-upon and consumed.

```java
Stream<String> stream = list.stream().filter(s -> s.length() > 3);

long count = stream.count();           // terminal op — stream is now consumed
List<String> result = stream.collect(Collectors.toList()); // THROWS:
// IllegalStateException: stream has already been operated upon or closed
```

**Why**: The stream's `AbstractPipeline` sets a `linkedOrConsumed` flag after first terminal op. Subsequent terminal ops check this flag.

**Fix**: Create a new stream each time, or use a `Supplier<Stream<T>>`:
```java
Supplier<Stream<String>> streamSupplier = () -> list.stream().filter(s -> s.length() > 3);
long count = streamSupplier.get().count();
List<String> result = streamSupplier.get().collect(toList());
```

---

### Q26. What is the `ConcurrentModificationException` risk with streams?

Stream pipelines use fail-fast Spliterators. If the source collection is modified during stream execution, you get a `ConcurrentModificationException` — even in single-threaded code.

```java
List<String> list = new ArrayList<>(List.of("a", "b", "c"));

// THROWS ConcurrentModificationException
list.stream()
    .filter(s -> s.equals("b"))
    .forEach(s -> list.remove(s));   // modifying source during stream!

// FIX 1: collect to new list first
list.removeAll(
    list.stream()
        .filter(s -> s.equals("b"))
        .collect(Collectors.toList())
);

// FIX 2: use removeIf (designed for this)
list.removeIf(s -> s.equals("b"));
```

**Parallel stream + mutable shared state**:
```java
List<Integer> results = new ArrayList<>();
// RACE CONDITION — ArrayList is not thread-safe
list.parallelStream().filter(x -> x > 0).forEach(results::add);

// FIX: use collect
List<Integer> results = list.parallelStream()
    .filter(x -> x > 0)
    .collect(Collectors.toList());
```

---

### Q27. Tricky: what does `Stream.of(int[])` give you vs `Arrays.stream(int[])`?

```java
int[] arr = {1, 2, 3};

// Stream.of(arr) — treats the array as a single object
Stream<int[]> s1 = Stream.of(arr);    // Stream containing ONE element (the array itself)
s1.count();  // 1 — NOT 3!

// Arrays.stream(arr) — correctly streams the elements
IntStream s2 = Arrays.stream(arr);    // IntStream with elements 1, 2, 3
s2.count();  // 3

// For Integer[] (object array), Stream.of works correctly
Integer[] objArr = {1, 2, 3};
Stream<Integer> s3 = Stream.of(objArr);  // Stream<Integer> with 3 elements ✓
```

**Why**: `Stream.of(T... values)` is `@SafeVarargs`. When passed an `int[]`, Java sees it as a single `T` (a reference to the array), not varargs of ints.

---

### Q28. `Collectors.toMap` with null values — what breaks and how do you fix it?

```java
// User with nullable email
Map<String, String> emailByName = users.stream()
    .collect(Collectors.toMap(
        User::getName,
        User::getEmail  // throws NullPointerException if email is null!
    ));
```

`toMap` uses `HashMap.merge()` internally, which throws NPE if value is null.

```java
// FIX: manual collection using forEach
Map<String, String> emailByName = new HashMap<>();
users.forEach(u -> emailByName.put(u.getName(), u.getEmail())); // allows null values

// FIX 2: replace null with sentinel
Map<String, String> emailByName = users.stream()
    .collect(Collectors.toMap(
        User::getName,
        u -> u.getEmail() != null ? u.getEmail() : ""
    ));

// FIX 3: use Optional as value
Map<String, Optional<String>> emailByName = users.stream()
    .collect(Collectors.toMap(
        User::getName,
        u -> Optional.ofNullable(u.getEmail())
    ));
```

---

## 11. Java 9–25 Stream Additions

### Q29. What stream features were added from Java 9 to Java 24? Which ones do interviewers ask about?

**Java 9**:
```java
// Stream.ofNullable — empty stream if null, single-element stream otherwise
Stream.ofNullable(null).count();     // 0
Stream.ofNullable("hello").count();  // 1

// Useful to avoid null checks in flatMap:
users.stream()
    .flatMap(u -> Stream.ofNullable(u.getEmail()))
    .collect(toList());

// takeWhile / dropWhile (see Q6)
// iterate with predicate (see Q23)

// Optional.stream() — bridges Optional to Stream
Optional<User> opt = findUser(id);
List<String> emails = opt.stream()  // Stream<User> with 0 or 1 elements
    .map(User::getEmail)
    .collect(toList());

// Use in flatMap to filter out empties:
List<String> emails = userIds.stream()
    .map(this::findUser)           // Stream<Optional<User>>
    .flatMap(Optional::stream)     // Stream<User>, empties removed
    .map(User::getEmail)
    .collect(toList());
```

**Java 12**: `Collectors.teeing` (see Q11)

**Java 16**:
```java
// Stream.toList() — returns unmodifiable list, more concise than Collectors.toList()
List<String> names = users.stream().map(User::getName).toList();
// names.add(...) → UnsupportedOperationException

// mapMulti — see Q4

// Stream.toList() vs Collectors.toList():
// - Stream.toList(): unmodifiable, more concise
// - Collectors.toList(): modifiable, allows further manipulation
```

**Java 22 (preview) → Java 24 (standard)**:
```java
// Stream.gather(Gatherer) — custom intermediate operations
// Gatherer is like a Collector but for intermediate stages

// Built-in Gatherers (java.util.stream.Gatherers):
import java.util.stream.Gatherers;

// Sliding window of size 3
Stream.of(1,2,3,4,5)
    .gather(Gatherers.windowSliding(3))
    .forEach(System.out::println);
// [1,2,3], [2,3,4], [3,4,5]

// Fixed window (non-overlapping)
Stream.of(1,2,3,4,5,6)
    .gather(Gatherers.windowFixed(2))
    .forEach(System.out::println);
// [1,2], [3,4], [5,6]

// fold (like reduce but can produce different type)
Optional<Integer> product = Stream.of(1,2,3,4,5)
    .gather(Gatherers.fold(() -> 1, (acc, n) -> acc * n))
    .findFirst();

// scan (running totals)
Stream.of(1,2,3,4,5)
    .gather(Gatherers.scan(() -> 0, Integer::sum))
    .toList();
// [1, 3, 6, 10, 15]
```

---

## 12. Streams vs Loops — Production Decisions

### Q30. When should you use a loop instead of a stream? What are the performance tradeoffs?

**Use a loop when**:
1. You need `break`/`continue` with complex state — streams have no equivalent (`findFirst` only covers simple early exit)
2. You need to modify multiple variables per iteration
3. Inner loop of a performance-critical section with small collections (< 100 elements) — stream overhead from object creation, lambda dispatch can exceed the computation
4. Checked exceptions — streams require wrapping in unchecked
5. Debugging is critical — stack traces through lambda layers are harder to read
6. The logic is inherently imperative with multiple interdependent state variables

**Use a stream when**:
1. Pipeline of transformations → readability is the primary win
2. Parallel execution is beneficial
3. Composition of operations (filter + map + collect pattern)
4. Working with Optional-returning methods (chaining)

**Performance reality** (benchmark-informed):
```java
// For large datasets (100k+ elements), streams and loops are roughly equal in speed
// For tiny datasets, loops can be 2-5x faster due to:
// - Lambda dispatch (invokeDynamic) overhead
// - Iterator object allocation
// - Pipeline setup cost
// - Boxing for primitive operations

// Worst case: don't box unnecessarily
// BAD: Stream<Integer> for arithmetic
Stream.of(1,2,3,4,5).mapToInt(Integer::intValue).sum()
// BETTER: IntStream from the start
IntStream.of(1,2,3,4,5).sum()
```

---

## 13. Functional Programming Concepts

### Q31. Why must variables captured in a lambda be effectively final? What does the JVM actually do?

Lambdas are compiled to methods on synthetic classes (via `invokedynamic`). Captured variables become fields of the generated object. If the variable could change after capture, the lambda would have a stale copy — a hidden data race.

```java
int count = 0;
// COMPILE ERROR — count is not effectively final
list.stream().forEach(s -> count++);   // ERROR

// WHY: the lambda captures the VALUE of count at creation time
// Modifying count after would be a logical error (stale value in lambda)

// Workaround 1: use AtomicInteger for mutable counter
AtomicInteger count = new AtomicInteger(0);
list.stream().forEach(s -> count.incrementAndGet());

// Workaround 2: use reduce/collect (idiomatic)
long count = list.stream().filter(predicate).count();

// Effectively final — not declared final but never reassigned
String prefix = "Hello";  // effectively final — OK to capture
list.stream().filter(s -> s.startsWith(prefix)).collect(toList());
```

---

### Q32. Memoization pattern with streams — implement a caching function transformer.

```java
// Generic memoize function — wraps any Function with a cache
public static <T, R> Function<T, R> memoize(Function<T, R> fn) {
    Map<T, R> cache = new ConcurrentHashMap<>();
    return input -> cache.computeIfAbsent(input, fn);
}

// Usage — expensive computation cached on first call
Function<Integer, Long> fibonacci = memoize(n -> {
    if (n <= 1) return (long) n;
    return fibonacci.apply(n - 1) + fibonacci.apply(n - 2); // Note: recursive ref won't work directly
});

// Better for recursive memoization:
Map<Integer, Long> cache = new ConcurrentHashMap<>();
Function<Integer, Long> fib = null;
fib = n -> cache.computeIfAbsent(n,
    k -> k <= 1 ? k : fib.apply(k - 1) + fib.apply(k - 2));

// In streams — avoid recomputing expensive derivations
List<Report> reports = userIds.stream()
    .map(memoize(this::fetchUserFromDB))   // DB call cached
    .map(User::generateReport)
    .collect(toList());
```

---

## 14. Coding Problems (Most Asked)

### Q33. Find the top 3 highest-paid employees per department.

```java
Map<String, List<Employee>> top3PerDept = employees.stream()
    .collect(Collectors.groupingBy(
        Employee::getDepartment,
        Collectors.collectingAndThen(
            Collectors.toList(),
            list -> list.stream()
                .sorted(Comparator.comparingDouble(Employee::getSalary).reversed())
                .limit(3)
                .collect(Collectors.toList())
        )
    ));

// Alternative using custom TopNCollector from Q14
Map<String, List<Employee>> top3PerDept = employees.stream()
    .collect(Collectors.groupingBy(
        Employee::getDepartment,
        TopNCollector.of(3, Comparator.comparingDouble(Employee::getSalary))
    ));
```

---

### Q34. Find all duplicate elements in a list and return them (not just true/false).

```java
List<Integer> numbers = List.of(1, 2, 3, 2, 4, 3, 5, 1);

// Approach 1: groupingBy + filter
Set<Integer> duplicates = numbers.stream()
    .collect(Collectors.groupingBy(Function.identity(), Collectors.counting()))
    .entrySet().stream()
    .filter(e -> e.getValue() > 1)
    .map(Map.Entry::getKey)
    .collect(Collectors.toSet());
// {1, 2, 3}

// Approach 2: using a Set as seen-tracker (more efficient, O(n))
Set<Integer> seen = new HashSet<>();
Set<Integer> duplicates = numbers.stream()
    .filter(n -> !seen.add(n))   // add returns false if already present
    .collect(Collectors.toSet());

// Note: approach 2 is stateful (seen set is external mutable state)
// NOT safe for parallel streams without synchronization
```

---

### Q35. Group anagrams from a list of strings.

```java
List<String> words = List.of("eat", "tea", "tan", "ate", "nat", "bat");

Map<String, List<String>> anagramGroups = words.stream()
    .collect(Collectors.groupingBy(word -> {
        char[] chars = word.toCharArray();
        Arrays.sort(chars);
        return new String(chars);  // sorted chars = canonical key
    }));

// Result: {aet=[eat, tea, ate], ant=[tan, nat], abt=[bat]}

// Get only groups with more than one anagram
Map<String, List<String>> actualAnagrams = words.stream()
    .collect(Collectors.groupingBy(word -> {
        char[] chars = word.toCharArray();
        Arrays.sort(chars);
        return new String(chars);
    }))
    .entrySet().stream()
    .filter(e -> e.getValue().size() > 1)
    .collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue));
```

---

### Q36. Merge two maps, summing values for duplicate keys.

```java
Map<String, Integer> map1 = Map.of("a", 1, "b", 2, "c", 3);
Map<String, Integer> map2 = Map.of("b", 20, "c", 30, "d", 40);

// Using Stream.concat + groupingBy + summingInt
Map<String, Integer> merged = Stream.concat(
        map1.entrySet().stream(),
        map2.entrySet().stream()
    )
    .collect(Collectors.groupingBy(
        Map.Entry::getKey,
        Collectors.summingInt(Map.Entry::getValue)
    ));
// {a=1, b=22, c=33, d=40}

// Alternative using Map.merge
Map<String, Integer> merged = new HashMap<>(map1);
map2.forEach((k, v) -> merged.merge(k, v, Integer::sum));
```

---

### Q37. Find the first non-repeating character in a string.

```java
String input = "swiss";

Optional<Character> firstUnique = input.chars()
    .mapToObj(c -> (char) c)
    .collect(Collectors.groupingBy(Function.identity(), LinkedHashMap::new, Collectors.counting()))
    .entrySet().stream()
    .filter(e -> e.getValue() == 1)
    .map(Map.Entry::getKey)
    .findFirst();

// 'w'

// LinkedHashMap preserves insertion order — critical for "first" requirement
// Without it, HashMap gives arbitrary order
```

---

### Q38. Running total (prefix sum) using streams.

```java
List<Integer> numbers = List.of(1, 2, 3, 4, 5);

// Java 22+ with Gatherers.scan:
List<Integer> runningTotal = numbers.stream()
    .gather(Gatherers.scan(() -> 0, Integer::sum))
    .toList();
// [1, 3, 6, 10, 15]

// Java 8-21: use AtomicInteger (not pure functional but works)
AtomicInteger running = new AtomicInteger(0);
List<Integer> runningTotal = numbers.stream()
    .map(n -> running.addAndGet(n))
    .collect(Collectors.toList());

// Or: convert to array, then IntStream.range
int[] arr = numbers.stream().mapToInt(Integer::intValue).toArray();
List<Integer> runningTotal = IntStream.range(0, arr.length)
    .map(i -> IntStream.rangeClosed(0, i).map(j -> arr[j]).sum())
    .boxed()
    .collect(Collectors.toList());
// Note: above is O(n²) — AtomicInteger approach is O(n)
```

---

### Q39. Partition a list into sublists of size N.

```java
// Java 22+ with Gatherers.windowFixed:
List<List<Integer>> partitions = list.stream()
    .gather(Gatherers.windowFixed(3))
    .toList();

// Java 8-21:
public static <T> List<List<T>> partition(List<T> list, int size) {
    return IntStream.range(0, (list.size() + size - 1) / size)
        .mapToObj(i -> list.subList(
            i * size,
            Math.min((i + 1) * size, list.size())
        ))
        .collect(Collectors.toList());
}

// Usage: batch processing (e.g., insert 1000 records at a time)
partition(userIds, 1000).stream()
    .forEach(batch -> db.batchInsert(batch));
```

---

### Q40. Convert a list of strings to a frequency map and find the most common word.

```java
List<String> words = List.of("apple", "banana", "apple", "cherry", "banana", "apple");

// Frequency map
Map<String, Long> freq = words.stream()
    .collect(Collectors.groupingBy(Function.identity(), Collectors.counting()));

// Most common word
Optional<String> mostCommon = freq.entrySet().stream()
    .max(Map.Entry.comparingByValue())
    .map(Map.Entry::getKey);
// "apple"

// Top N most common
List<String> topN = freq.entrySet().stream()
    .sorted(Map.Entry.<String, Long>comparingByValue().reversed())
    .limit(2)
    .map(Map.Entry::getKey)
    .collect(Collectors.toList());
// ["apple", "banana"]
```

---

### Q41. Transpose a matrix using streams.

```java
int[][] matrix = {
    {1, 2, 3},
    {4, 5, 6},
    {7, 8, 9}
};

int rows = matrix.length;
int cols = matrix[0].length;

int[][] transposed = IntStream.range(0, cols)
    .mapToObj(col ->
        IntStream.range(0, rows)
            .map(row -> matrix[row][col])
            .toArray()
    )
    .toArray(int[][]::new);

// transposed[0] = {1, 4, 7}
// transposed[1] = {2, 5, 8}
// transposed[2] = {3, 6, 9}
```

---

### Q42. Second highest salary — multiple approaches.

```java
List<Employee> employees = ...;

// Approach 1: distinct + sorted + skip + findFirst
Optional<Double> secondHighest = employees.stream()
    .map(Employee::getSalary)
    .distinct()
    .sorted(Comparator.reverseOrder())
    .skip(1)
    .findFirst();

// Approach 2: using TreeSet (also deduplicates)
Optional<Double> secondHighest = employees.stream()
    .map(Employee::getSalary)
    .collect(Collectors.toCollection(() -> new TreeSet<>(Comparator.reverseOrder())))
    .stream()
    .skip(1)
    .findFirst();

// Approach 3: single pass using reduce (avoids full sort)
// Track top-2 as we go
double[] top2 = employees.stream()
    .map(Employee::getSalary)
    .distinct()
    .reduce(
        new double[]{Double.MIN_VALUE, Double.MIN_VALUE},
        (arr, salary) -> {
            if (salary > arr[0]) return new double[]{salary, arr[0]};
            if (salary > arr[1]) return new double[]{arr[0], salary};
            return arr;
        },
        (a, b) -> {  // combiner for parallel
            double[] merged = new double[]{
                Math.max(a[0], b[0]),
                Math.max(Math.min(a[0], b[0]), Math.max(a[1], b[1]))
            };
            return merged;
        }
    );
// top2[1] is second highest
```

---

## 15. Production Scenarios & Debugging

### Q43. `Files.lines()` memory leak — what causes it and how do you fix it?

```java
// MEMORY LEAK — stream not closed, underlying file descriptor held open
Stream<String> lines = Files.lines(Paths.get("large.log"));
long count = lines.filter(l -> l.contains("ERROR")).count();
// File descriptor leaked — never closed!

// FIX: try-with-resources (Stream implements AutoCloseable)
long count;
try (Stream<String> lines = Files.lines(Paths.get("large.log"))) {
    count = lines.filter(l -> l.contains("ERROR")).count();
}

// WHY: Files.lines() opens a BufferedReader internally.
// The stream registers an onClose() handler to close the reader.
// Only calling stream.close() (or try-with-resources) triggers it.

// MEMORY: Files.lines() is lazy — reads line-by-line, O(1) memory regardless of file size
// vs Files.readAllLines() — loads entire file into memory, O(n)

// For very large files (GB-scale):
try (Stream<String> lines = Files.lines(path, StandardCharsets.UTF_8)) {
    lines.parallel()   // safe: file-backed spliterator supports splitting
        .filter(l -> l.startsWith("ERROR"))
        .forEach(errorLog::append);
}
```

---

### Q44. ThreadLocal not propagated in parallel streams — explain and fix.

```java
// SLF4J MDC uses ThreadLocal for request context
MDC.put("requestId", "REQ-123");

// Sequential stream — same thread, MDC works
list.stream()
    .map(this::processItem)   // MDC.get("requestId") = "REQ-123" ✓
    .collect(toList());

// Parallel stream — ForkJoin threads don't inherit caller's ThreadLocal
list.parallelStream()
    .map(this::processItem)   // MDC.get("requestId") = null ✗
    .collect(toList());
```

**Fix**: Capture the MDC context before the stream and propagate it:

```java
Map<String, String> contextMap = MDC.getCopyOfContextMap();

list.parallelStream()
    .map(item -> {
        MDC.setContextMap(contextMap);   // restore on each worker thread
        try {
            return processItem(item);
        } finally {
            MDC.clear();                  // clean up to prevent leaks
        }
    })
    .collect(toList());
```

**Better**: Use `CompletableFuture` with a custom executor wrapper that propagates context.

---

### Q45. Debug a stream pipeline — what tools and techniques do you use?

```java
// 1. peek() for intermediate inspection (development only)
List<String> result = list.stream()
    .peek(s -> log.debug("before filter: {}", s))
    .filter(s -> s.length() > 3)
    .peek(s -> log.debug("after filter: {}", s))
    .map(String::toUpperCase)
    .peek(s -> log.debug("after map: {}", s))
    .collect(toList());

// 2. Break pipeline at a point — collect to list and inspect
List<String> filtered = list.stream()
    .filter(s -> s.length() > 3)
    .collect(toList());
// inspect 'filtered' in debugger, then continue:
List<String> result = filtered.stream()
    .map(String::toUpperCase)
    .collect(toList());

// 3. IntelliJ Java Stream Debugger — visual tool
// Breakpoint on stream terminal op → "Trace Current Stream Chain"
// Shows element flow through each stage visually

// 4. Exception in lambda — improve stack traces
list.stream()
    .map(item -> {
        try {
            return riskyOperation(item);
        } catch (Exception e) {
            throw new RuntimeException("Failed processing: " + item, e);
            // adds item context to stack trace
        }
    })
    .collect(toList());

// 5. JFR for production profiling — stream allocation hotspots
// jcmd <PID> JFR.start duration=60s filename=stream-profile.jfr
// Open in JDK Mission Control → Allocation tab → filter for stream lambdas
```

---

## 16. Rapid-Fire Round

### Q46. Output prediction questions.

**Q: What does this print?**
```java
Stream.of("one", "two", "three")
    .filter(s -> {
        System.out.println("filter: " + s);
        return s.length() > 2;
    })
    .map(s -> {
        System.out.println("map: " + s);
        return s.toUpperCase();
    })
    .findFirst()
    .ifPresent(System.out::println);
```
**A**:
```
filter: one    ← "one" has length 3, passes filter
map: one       ← immediately goes to map
ONE            ← findFirst short-circuits here, "two" and "three" never processed
```

---

**Q: What is the output?**
```java
List<Integer> list = new ArrayList<>(List.of(1, 2, 3, 4, 5));
list.stream()
    .filter(n -> n % 2 == 0)
    .forEach(list::remove);
```
**A**: `ConcurrentModificationException` — modifying `list` while iterating it via stream.

---

**Q: What does `Stream.of(new int[]{1,2,3}).count()` return?**
**A**: `1` — not `3`. `Stream.of(int[])` treats the array as a single element (`Stream<int[]>`). Use `Arrays.stream(new int[]{1,2,3}).count()` → `3`.

---

**Q: Will this compile? What does it return?**
```java
Optional<String> opt = Optional.of("hello");
Optional<Optional<String>> result = opt.map(Optional::of);
```
**A**: Compiles. Returns `Optional[Optional[hello]]`. Use `flatMap(Optional::of)` to get `Optional[hello]`.

---

**Q: `Collectors.toList()` vs `Stream.toList()` (Java 16) — what's the difference?**

| | `Collectors.toList()` | `Stream.toList()` |
|---|---|---|
| Mutability | Mutable (add/remove allowed) | **Unmodifiable** |
| Null elements | Allows nulls | Allows nulls |
| Since | Java 8 | Java 16 |
| Verbosity | `.collect(Collectors.toList())` | `.toList()` |

---

**Q: What happens when `groupingBy` classifier returns null?**
```java
Map<String, List<String>> grouped = Stream.of("a", null, "b")
    .collect(Collectors.groupingBy(s -> s == null ? null : s.toUpperCase()));
```
**A**: `NullPointerException` — `groupingBy` uses `HashMap` which allows null keys, but the grouping operation calls `HashMap.computeIfAbsent(null, ...)` which works. Actually — this **does** work in Java 8 (null key allowed in HashMap). However, `groupingBy(Function.identity())` on a stream containing null elements throws NPE because it calls the classifier function which tries to unbox null. Test carefully — behavior depends on the classifier implementation.

---

**Q: `partitioningBy` vs `groupingBy` — when must you use `partitioningBy`?**

`partitioningBy(Predicate)` always produces `Map<Boolean, List<T>>` with both `true` and `false` keys present (even if one list is empty). `groupingBy` only creates keys that actually appear. Use `partitioningBy` when you need guaranteed presence of both groups:

```java
// partitioningBy — always has both keys
Map<Boolean, List<Integer>> evenOdd = numbers.stream()
    .collect(Collectors.partitioningBy(n -> n % 2 == 0));
evenOdd.get(true);   // evens — never null
evenOdd.get(false);  // odds  — never null

// groupingBy equivalent — key may be missing if no elements match
Map<String, List<Integer>> grouped = numbers.stream()
    .collect(Collectors.groupingBy(n -> n % 2 == 0 ? "even" : "odd"));
grouped.get("even"); // could be null if no even numbers!
```

---

## Production Cheat Sheet

### Stream Operation Selection Guide

| Need | Use |
|---|---|
| Transform each element | `map` |
| Flatten nested collections | `flatMap` |
| Filter elements | `filter` |
| Stop at condition (ordered) | `takeWhile` (Java 9) |
| Skip until condition | `dropWhile` (Java 9) |
| Custom intermediate op | `gather(Gatherer)` (Java 22+) |
| Group elements | `Collectors.groupingBy` |
| Partition into two | `Collectors.partitioningBy` |
| Sum/count/average | `Collectors.summingInt/counting/averagingInt` |
| Two collectors simultaneously | `Collectors.teeing` (Java 12) |
| Post-process collector result | `Collectors.collectingAndThen` |
| Key-value map | `Collectors.toMap` + merge function |
| Mutable reduction | `collect` (not `reduce`) |
| Immutable reduction | `reduce` with identity |
| First match | `findFirst` (sequential) / `findAny` (parallel) |
| Check existence | `anyMatch` / `allMatch` / `noneMatch` |
| Primitive arithmetic | `IntStream` / `LongStream` / `DoubleStream` |
| Large data + CPU-bound | `parallelStream` with `unordered()` |
| Large data + I/O | `CompletableFuture` + dedicated executor |

### Common Bugs

| Bug | Fix |
|---|---|
| Stream reuse | Create new stream per operation or use `Supplier<Stream<T>>` |
| `toMap` NPE on null values | Collect to `HashMap` with `forEach` |
| `toMap` duplicate key | Add merge function |
| Parallel stream + shared mutable state | Use `collect` or thread-safe containers |
| `Stream.of(int[])` wrong count | Use `Arrays.stream(int[])` |
| `Files.lines` file leak | Use `try-with-resources` |
| MDC lost in parallel stream | Capture and restore context map per element |
| Infinite stream hanging | Ensure short-circuit terminal or `limit()` |
| `orElse` evaluating always | Switch to `orElseGet` with Supplier |
| Modifying source during stream | Use `removeIf`, `replaceAll`, or collect first |
