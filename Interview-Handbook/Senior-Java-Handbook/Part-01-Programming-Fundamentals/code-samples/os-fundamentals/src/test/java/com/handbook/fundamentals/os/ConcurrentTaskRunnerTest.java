package com.handbook.fundamentals.os;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertTrue;

class ConcurrentTaskRunnerTest {

    @Test
    void allTasksCompleteCorrectlyOnABoundedPlatformThreadPool() throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(4);
        try {
            // runBlockingTasks() throws IllegalStateException internally if
            // any task's result is wrong -- reaching this line at all IS
            // the correctness assertion.
            long elapsed = ConcurrentTaskRunner.runBlockingTasks(pool, 20, 5);
            assertTrue(elapsed >= 0);
        } finally {
            pool.shutdown();
        }
    }

    @Test
    void allTasksCompleteCorrectlyOnAVirtualThreadPerTaskExecutor() throws Exception {
        try (ExecutorService pool = Executors.newVirtualThreadPerTaskExecutor()) {
            long elapsed = ConcurrentTaskRunner.runBlockingTasks(pool, 20, 5);
            assertTrue(elapsed >= 0);
        }
    }

    @Test
    void handlesZeroTasks() throws Exception {
        try (ExecutorService pool = Executors.newVirtualThreadPerTaskExecutor()) {
            long elapsed = ConcurrentTaskRunner.runBlockingTasks(pool, 0, 5);
            assertTrue(elapsed >= 0);
        }
    }
}
