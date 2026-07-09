package com.handbook.fundamentals.complexity;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class SearchAlgorithmsTest {

    private static final int[] SORTED = {1, 3, 5, 7, 9, 11, 13, 15, 17, 19};

    @Test
    void linearSearchFindsPresentElementAtCorrectIndex() {
        assertEquals(0, SearchAlgorithms.linearSearch(SORTED, 1));
        assertEquals(4, SearchAlgorithms.linearSearch(SORTED, 9));
        assertEquals(9, SearchAlgorithms.linearSearch(SORTED, 19));
    }

    @Test
    void linearSearchReturnsNegativeOneForAbsentElement() {
        assertEquals(-1, SearchAlgorithms.linearSearch(SORTED, 4));
        assertEquals(-1, SearchAlgorithms.linearSearch(SORTED, 100));
    }

    @Test
    void binarySearchFindsPresentElementAtCorrectIndex() {
        assertEquals(0, SearchAlgorithms.binarySearch(SORTED, 1));
        assertEquals(4, SearchAlgorithms.binarySearch(SORTED, 9));
        assertEquals(9, SearchAlgorithms.binarySearch(SORTED, 19));
    }

    @Test
    void binarySearchReturnsNegativeOneForAbsentElement() {
        assertEquals(-1, SearchAlgorithms.binarySearch(SORTED, 4));
        assertEquals(-1, SearchAlgorithms.binarySearch(SORTED, 100));
    }

    @Test
    void bothAlgorithmsAgreeOnEmptyArray() {
        int[] empty = {};
        assertEquals(-1, SearchAlgorithms.linearSearch(empty, 5));
        assertEquals(-1, SearchAlgorithms.binarySearch(empty, 5));
    }

    @Test
    void bothAlgorithmsAgreeOnSingleElementArray() {
        int[] single = {42};
        assertEquals(0, SearchAlgorithms.linearSearch(single, 42));
        assertEquals(0, SearchAlgorithms.binarySearch(single, 42));
        assertEquals(-1, SearchAlgorithms.linearSearch(single, 7));
        assertEquals(-1, SearchAlgorithms.binarySearch(single, 7));
    }

    @Test
    void bothAlgorithmsProduceTheSameResultAcrossEveryElementOfALargerArray() {
        int[] sorted = new int[1000];
        for (int i = 0; i < sorted.length; i++) {
            sorted[i] = i * 3;
        }
        for (int i = 0; i < sorted.length; i++) {
            int target = sorted[i];
            assertEquals(SearchAlgorithms.linearSearch(sorted, target),
                    SearchAlgorithms.binarySearch(sorted, target),
                    "both algorithms must agree on every index for target " + target);
        }
    }
}
