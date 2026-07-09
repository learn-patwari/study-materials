package com.handbook.fundamentals.cache;

import java.util.concurrent.CountDownLatch;

/**
 * Manual timing demonstration for both cache-behavior examples in this
 * package. Not run as part of the JUnit suite — wall-clock timing
 * comparisons are inherently noisy (JIT warmup, OS scheduling, other load
 * on the machine) and make a flaky, non-deterministic test. Run this
 * directly to see the effect for yourself:
 *
 * <pre>
 *   mvn -q compile
 *   java -cp target/classes com.handbook.fundamentals.cache.BenchmarkRunner
 * </pre>
 *
 * <p>Correctness (both approaches produce identical results) is what the
 * JUnit tests in this module actually assert — performance is the
 * qualitative, illustrative point this class demonstrates, not something
 * to gate a build on.
 */
public final class BenchmarkRunner {

    private BenchmarkRunner() {
    }

    public static void main(String[] args) throws InterruptedException {
        falseSharingDemo();
        System.out.println();
        matrixTraversalDemo();
    }

    private static void falseSharingDemo() throws InterruptedException {
        int threads = 4;
        long iterations = 200_000_000L;

        long unpaddedMillis = timeCounters(new UnpaddedCounters(threads), threads, iterations);
        long paddedMillis = timeCounters(new PaddedCounters(threads), threads, iterations);

        System.out.println("False sharing demo (" + threads + " threads x " + iterations + " increments each):");
        System.out.println("  Unpadded (false-shared) counters: " + unpaddedMillis + " ms");
        System.out.println("  Padded (isolated) counters:       " + paddedMillis + " ms");
        System.out.println("  (Padded is typically several times faster under contention on multi-core hardware.)");
    }

    private static long timeCounters(Object counters, int threads, long iterations) throws InterruptedException {
        CountDownLatch ready = new CountDownLatch(threads);
        CountDownLatch start = new CountDownLatch(1);
        Thread[] workers = new Thread[threads];

        for (int t = 0; t < threads; t++) {
            int index = t;
            workers[t] = new Thread(() -> {
                ready.countDown();
                try {
                    start.await();
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    return;
                }
                if (counters instanceof UnpaddedCounters unpadded) {
                    unpadded.incrementNTimes(index, iterations);
                } else if (counters instanceof PaddedCounters padded) {
                    padded.incrementNTimes(index, iterations);
                }
            });
        }

        for (Thread w : workers) {
            w.start();
        }
        ready.await();
        long startNanos = System.nanoTime();
        start.countDown();
        for (Thread w : workers) {
            w.join();
        }
        return (System.nanoTime() - startNanos) / 1_000_000;
    }

    private static void matrixTraversalDemo() {
        int size = 4000;
        int[][] matrix = new int[size][size];
        for (int i = 0; i < size; i++) {
            for (int j = 0; j < size; j++) {
                matrix[i][j] = (i + j) % 7;
            }
        }

        long startRow = System.nanoTime();
        long rowSum = MatrixTraversal.sumRowMajor(matrix);
        long rowMillis = (System.nanoTime() - startRow) / 1_000_000;

        long startCol = System.nanoTime();
        long colSum = MatrixTraversal.sumColumnMajor(matrix);
        long colMillis = (System.nanoTime() - startCol) / 1_000_000;

        System.out.println("Matrix traversal demo (" + size + "x" + size + "):");
        System.out.println("  Row-major sum:    " + rowSum + " in " + rowMillis + " ms");
        System.out.println("  Column-major sum: " + colSum + " in " + colMillis + " ms");
        System.out.println("  (Same sum both ways -- column-major is typically several times slower due to cache misses.)");
    }
}
