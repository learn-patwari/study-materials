package com.handbook.fundamentals.os;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Random;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Manual timing demonstration for both comparisons in this package. Not
 * run as part of the JUnit suite -- see Chapter 01.01's {@code
 * BenchmarkRunner} for the same rationale (wall-clock timing is noisy;
 * correctness is what the JUnit tests assert).
 *
 * <pre>
 *   mvn -q compile
 *   java -cp target/classes com.handbook.fundamentals.os.BenchmarkRunner
 * </pre>
 */
public final class BenchmarkRunner {

    private BenchmarkRunner() {
    }

    public static void main(String[] args) throws InterruptedException, ExecutionException, IOException {
        threadModelDemo();
        System.out.println();
        ioDemo();
    }

    private static void threadModelDemo() throws InterruptedException, ExecutionException {
        int taskCount = 3000;
        long blockMillis = 20;

        long platformElapsed;
        ExecutorService platformPool = Executors.newFixedThreadPool(200);
        try {
            platformElapsed = ConcurrentTaskRunner.runBlockingTasks(platformPool, taskCount, blockMillis);
        } finally {
            platformPool.shutdown();
        }

        long virtualElapsed;
        try (ExecutorService virtualPool = Executors.newVirtualThreadPerTaskExecutor()) {
            virtualElapsed = ConcurrentTaskRunner.runBlockingTasks(virtualPool, taskCount, blockMillis);
        }

        System.out.println("Thread model demo (" + taskCount + " blocking tasks, " + blockMillis + "ms block each):");
        System.out.println("  Platform threads (bounded pool, size 200): " + platformElapsed + " ms");
        System.out.println("  Virtual threads (one per task):            " + virtualElapsed + " ms");
        System.out.println("  (A bounded platform pool serializes work in batches of 200;");
        System.out.println("   virtual threads don't tie up a scarce OS thread while blocked.)");
    }

    private static void ioDemo() throws IOException {
        Path tempFile = Files.createTempFile("os-fundamentals-io-demo", ".bin");
        try {
            byte[] data = new byte[2_000_000];
            new Random(11).nextBytes(data);
            Files.write(tempFile, data);

            long startUnbuffered = System.nanoTime();
            long checksumUnbuffered = BufferedIoDemo.readAllBytesUnbuffered(tempFile);
            long unbufferedMillis = (System.nanoTime() - startUnbuffered) / 1_000_000;

            long startBuffered = System.nanoTime();
            long checksumBuffered = BufferedIoDemo.readAllBytesBuffered(tempFile);
            long bufferedMillis = (System.nanoTime() - startBuffered) / 1_000_000;

            System.out.println("Buffered vs unbuffered I/O demo (" + data.length + " byte file, read one byte at a time):");
            System.out.println("  Unbuffered (FileInputStream):   " + unbufferedMillis + " ms");
            System.out.println("  Buffered (BufferedInputStream): " + bufferedMillis + " ms");
            System.out.println("  (Same checksum both ways: " + (checksumUnbuffered == checksumBuffered)
                    + " -- buffering avoids a syscall per byte.)");
        } finally {
            Files.deleteIfExists(tempFile);
        }
    }
}
