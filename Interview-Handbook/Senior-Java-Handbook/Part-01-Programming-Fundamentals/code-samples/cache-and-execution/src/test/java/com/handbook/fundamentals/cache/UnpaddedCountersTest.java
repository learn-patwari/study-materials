package com.handbook.fundamentals.cache;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class UnpaddedCountersTest {

    @Test
    void eachSlotIndependentlyReachesExactExpectedCount() throws InterruptedException {
        int threads = 4;
        long iterations = 100_000;
        UnpaddedCounters counters = new UnpaddedCounters(threads);

        runConcurrently(threads, index -> counters.incrementNTimes(index, iterations));

        for (int i = 0; i < threads; i++) {
            assertEquals(iterations, counters.get(i),
                    "each thread only ever writes its own slot, so no data race -- "
                            + "false sharing is a performance bug, not a correctness bug");
        }
    }

    static void runConcurrently(int threads, java.util.function.IntConsumer task) throws InterruptedException {
        Thread[] workers = new Thread[threads];
        for (int t = 0; t < threads; t++) {
            int index = t;
            workers[t] = new Thread(() -> task.accept(index));
        }
        for (Thread w : workers) {
            w.start();
        }
        for (Thread w : workers) {
            w.join();
        }
    }
}
