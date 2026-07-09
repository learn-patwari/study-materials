package com.handbook.fundamentals.complexity;

/**
 * Two ways to find a target value in a SORTED array — same result, very
 * different complexity classes. {@link #linearSearch} is O(n): it may
 * examine every element. {@link #binarySearch} is O(log n): it halves the
 * remaining search space on every comparison, exploiting the fact the
 * input is sorted (something linear search never uses).
 */
public final class SearchAlgorithms {

    private SearchAlgorithms() {
    }

    /** O(n). Works on sorted OR unsorted input -- doesn't exploit ordering at all. */
    public static int linearSearch(int[] array, int target) {
        for (int i = 0; i < array.length; i++) {
            if (array[i] == target) {
                return i;
            }
        }
        return -1;
    }

    /** O(log n). Requires sorted input -- the entire speedup comes from that precondition. */
    public static int binarySearch(int[] sortedArray, int target) {
        int low = 0;
        int high = sortedArray.length - 1;
        while (low <= high) {
            int mid = low + (high - low) / 2; // avoids (low+high) overflow for large arrays
            if (sortedArray[mid] == target) {
                return mid;
            } else if (sortedArray[mid] < target) {
                low = mid + 1;
            } else {
                high = mid - 1;
            }
        }
        return -1;
    }
}
