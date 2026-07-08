package com.handbook.urlshortener;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;
import java.util.stream.IntStream;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class RangeBasedIdGeneratorTest {

    @Test
    void neverReturnsDuplicateIdsSingleThreaded() {
        RangeBasedIdGenerator generator = new RangeBasedIdGenerator(10, new CountingAllocator());

        Set<Long> seen = new HashSet<>();
        for (int i = 0; i < 1000; i++) {
            long id = generator.nextId();
            assertTrue(seen.add(id), "duplicate id generated: " + id);
        }
    }

    @Test
    void claimsBlocksOfTheConfiguredSize() {
        CountingAllocator allocator = new CountingAllocator();
        RangeBasedIdGenerator generator = new RangeBasedIdGenerator(5, allocator);

        for (int i = 0; i < 5; i++) {
            generator.nextId();
        }
        assertEquals(1, allocator.claimCount(), "one block of 5 should satisfy exactly 5 requests");

        generator.nextId(); // 6th request must trigger a second block claim
        assertEquals(2, allocator.claimCount());
    }

    @Test
    void neverReturnsDuplicateIdsUnderConcurrentLoad() throws Exception {
        RangeBasedIdGenerator generator = new RangeBasedIdGenerator(50, new CountingAllocator());
        int threads = 8;
        int idsPerThread = 500;

        ExecutorService pool = Executors.newFixedThreadPool(threads);
        try {
            List<Callable<List<Long>>> tasks = IntStream.range(0, threads)
                    .<Callable<List<Long>>>mapToObj(t -> () -> {
                        List<Long> ids = new java.util.ArrayList<>(idsPerThread);
                        for (int i = 0; i < idsPerThread; i++) {
                            ids.add(generator.nextId());
                        }
                        return ids;
                    })
                    .collect(Collectors.toList());

            List<Future<List<Long>>> futures = pool.invokeAll(tasks);
            Set<Long> allIds = new HashSet<>();
            int total = 0;
            for (Future<List<Long>> f : futures) {
                for (Long id : f.get()) {
                    assertTrue(allIds.add(id), "duplicate id generated under concurrency: " + id);
                    total++;
                }
            }
            assertEquals(threads * idsPerThread, total);
        } finally {
            pool.shutdown();
            pool.awaitTermination(10, TimeUnit.SECONDS);
        }
    }

    /** Deterministic, non-shared-state allocator for assertions on block-claim count. */
    private static final class CountingAllocator implements RangeBasedIdGenerator.BlockAllocator {
        private final AtomicLong nextStart = new AtomicLong(0);
        private final AtomicLong claims = new AtomicLong(0);

        @Override
        public long claimBlockStart(int blockSize) {
            claims.incrementAndGet();
            return nextStart.getAndAdd(blockSize);
        }

        long claimCount() {
            return claims.get();
        }
    }
}
