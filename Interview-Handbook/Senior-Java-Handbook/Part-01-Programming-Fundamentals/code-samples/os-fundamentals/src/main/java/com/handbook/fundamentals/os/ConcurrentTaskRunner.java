package com.handbook.fundamentals.os;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Future;

/**
 * Runs a batch of blocking tasks against whichever {@link ExecutorService}
 * it's given. The interesting comparison (see {@code BenchmarkRunner}) is
 * what happens when the SAME method is handed a bounded platform-thread
 * pool vs. a virtual-thread-per-task executor for tasks that block
 * (simulated here with {@code Thread.sleep}, standing in for blocking I/O
 * — a DB call, an HTTP call, anything that parks the thread waiting on an
 * external response).
 */
public final class ConcurrentTaskRunner {

    private ConcurrentTaskRunner() {
    }

    /**
     * Submits {@code taskCount} tasks, each blocking for {@code blockMillis},
     * and returns total wall-clock time. Also verifies every task's result
     * is correct (throws if not) -- this is the correctness check the test
     * suite relies on, not a separate assertion helper.
     */
    public static long runBlockingTasks(ExecutorService executor, int taskCount, long blockMillis)
            throws InterruptedException, ExecutionException {
        List<Callable<Integer>> tasks = new ArrayList<>(taskCount);
        for (int i = 0; i < taskCount; i++) {
            int index = i;
            tasks.add(() -> {
                Thread.sleep(blockMillis);
                return index;
            });
        }

        long startNanos = System.nanoTime();
        List<Future<Integer>> futures = new ArrayList<>(taskCount);
        for (Callable<Integer> task : tasks) {
            futures.add(executor.submit(task));
        }
        long sum = 0;
        for (Future<Integer> future : futures) {
            sum += future.get();
        }
        long elapsedMillis = (System.nanoTime() - startNanos) / 1_000_000;

        long expectedSum = (long) taskCount * (taskCount - 1) / 2;
        if (sum != expectedSum) {
            throw new IllegalStateException(
                    "task results incorrect: expected sum " + expectedSum + " but got " + sum);
        }
        return elapsedMillis;
    }
}
