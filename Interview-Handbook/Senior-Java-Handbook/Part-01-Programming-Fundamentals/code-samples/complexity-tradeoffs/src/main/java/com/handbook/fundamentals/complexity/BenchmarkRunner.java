package com.handbook.fundamentals.complexity;

import java.util.Random;

/**
 * Manual timing demonstration for both complexity comparisons in this
 * package. Not run as part of the JUnit suite — see Chapter 01.01's
 * {@code BenchmarkRunner} for the same rationale (wall-clock timing is
 * noisy and makes a flaky test; correctness is what the JUnit tests
 * assert).
 *
 * <pre>
 *   mvn -q compile
 *   java -cp target/classes com.handbook.fundamentals.complexity.BenchmarkRunner
 * </pre>
 */
public final class BenchmarkRunner {

    private BenchmarkRunner() {
    }

    public static void main(String[] args) {
        searchDemo();
        System.out.println();
        lookupDemo();
    }

    private static void searchDemo() {
        int size = 10_000_000;
        int[] sortedArray = new int[size];
        for (int i = 0; i < size; i++) {
            sortedArray[i] = i * 2; // sorted, so binary search's precondition holds
        }
        int target = sortedArray[size - 1]; // worst case for linear search: last element

        long startLinear = System.nanoTime();
        int linearResult = SearchAlgorithms.linearSearch(sortedArray, target);
        long linearMicros = (System.nanoTime() - startLinear) / 1_000;

        long startBinary = System.nanoTime();
        int binaryResult = SearchAlgorithms.binarySearch(sortedArray, target);
        long binaryMicros = (System.nanoTime() - startBinary) / 1_000;

        System.out.println("Search demo (" + size + " sorted elements, worst-case target):");
        System.out.println("  Linear search (O(n)):     found at " + linearResult + " in " + linearMicros + " us");
        System.out.println("  Binary search (O(log n)): found at " + binaryResult + " in " + binaryMicros + " us");
        System.out.println("  (Binary search is typically orders of magnitude faster at this size.)");
    }

    private static void lookupDemo() {
        int size = 200_000;
        Random random = new Random(7);
        ListLookup listLookup = new ListLookup();
        HashLookup hashLookup = new HashLookup();
        for (int i = 0; i < size; i++) {
            int value = random.nextInt();
            listLookup.add(value);
            hashLookup.add(value);
        }
        int probeCount = 2_000;
        int missingValue = Integer.MIN_VALUE; // never added -- worst case for ListLookup (scans everything)

        long startList = System.nanoTime();
        for (int i = 0; i < probeCount; i++) {
            listLookup.contains(missingValue);
        }
        long listMillis = (System.nanoTime() - startList) / 1_000_000;

        long startHash = System.nanoTime();
        for (int i = 0; i < probeCount; i++) {
            hashLookup.contains(missingValue);
        }
        long hashMillis = (System.nanoTime() - startHash) / 1_000_000;

        System.out.println("Lookup demo (" + size + " elements, " + probeCount + " missing-value probes):");
        System.out.println("  ListLookup (O(n) per probe):  " + listMillis + " ms total");
        System.out.println("  HashLookup (O(1) per probe):  " + hashMillis + " ms total");
        System.out.println("  (HashLookup is typically orders of magnitude faster for repeated lookups at this size.)");
    }
}
