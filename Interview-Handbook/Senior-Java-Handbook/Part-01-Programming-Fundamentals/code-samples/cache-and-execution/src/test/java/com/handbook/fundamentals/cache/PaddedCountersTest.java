package com.handbook.fundamentals.cache;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class PaddedCountersTest {

    @Test
    void eachSlotIndependentlyReachesExactExpectedCount() throws InterruptedException {
        int threads = 4;
        long iterations = 100_000;
        PaddedCounters counters = new PaddedCounters(threads);

        UnpaddedCountersTest.runConcurrently(threads, index -> counters.incrementNTimes(index, iterations));

        for (int i = 0; i < threads; i++) {
            assertEquals(iterations, counters.get(i),
                    "padding changes performance, not correctness -- final counts must still be exact");
        }
    }

    @Test
    void differentLogicalIndicesMapToDifferentStripedSlots() {
        PaddedCounters counters = new PaddedCounters(3);
        counters.incrementNTimes(0, 5);
        counters.incrementNTimes(1, 7);
        counters.incrementNTimes(2, 11);

        assertEquals(5, counters.get(0));
        assertEquals(7, counters.get(1));
        assertEquals(11, counters.get(2));
    }
}
