package com.handbook.interview;

import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class PoisonPillWorkQueueTest {

    @Test
    void consumerReceivesAllProducedItemsInOrder() throws InterruptedException {
        PoisonPillWorkQueue<String> queue = new PoisonPillWorkQueue<>(10);

        queue.produce("task-1");
        queue.produce("task-2");
        queue.produce("task-3");
        queue.shutdown();

        List<String> processed = queue.consumeUntilShutdown();

        assertEquals(List.of("task-1", "task-2", "task-3"), processed);
    }

    @Test
    void consumerStopsCleanlyOnShutdownEvenWhenBlockedWaiting() throws Exception {
        PoisonPillWorkQueue<Integer> queue = new PoisonPillWorkQueue<>(5);
        ExecutorService pool = Executors.newSingleThreadExecutor();

        // Consumer starts FIRST and blocks in queue.take() with nothing
        // produced yet -- this is exactly the scenario a boolean "stop"
        // flag can't handle, since a parked take() isn't polling anything.
        Future<List<Integer>> future = pool.submit(queue::consumeUntilShutdown);

        Thread.sleep(50); // give the consumer time to actually park in take()
        queue.produce(42);
        queue.shutdown();

        List<Integer> processed = future.get(2, TimeUnit.SECONDS);
        assertEquals(List.of(42), processed);

        pool.shutdown();
        assertTrue(pool.awaitTermination(2, TimeUnit.SECONDS));
    }

    @Test
    void producerBlocksWhenQueueIsAtCapacity() throws Exception {
        PoisonPillWorkQueue<Integer> queue = new PoisonPillWorkQueue<>(1);
        queue.produce(1); // fills the only slot

        ExecutorService producerPool = Executors.newSingleThreadExecutor();
        Future<?> producerAttempt = producerPool.submit(() -> {
            try {
                queue.produce(2); // must block until the consumer drains slot 1
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        });

        // The producer should still be blocked shortly after submission,
        // since nothing has drained the queue yet -- this IS backpressure.
        Thread.sleep(50);
        assertTrue(!producerAttempt.isDone());

        // Start the consumer BEFORE calling shutdown(): shutdown() itself
        // calls the blocking put(POISON_PILL), which would deadlock this
        // test thread if called while the queue is still full and nothing
        // is draining it.
        ExecutorService consumerPool = Executors.newSingleThreadExecutor();
        Future<List<Integer>> consumerFuture = consumerPool.submit(queue::consumeUntilShutdown);

        producerAttempt.get(2, TimeUnit.SECONDS); // unblocks once the consumer drains item 1
        queue.shutdown(); // may itself block briefly until item 2 is drained -- consumer is running, so it won't hang
        List<Integer> processed = consumerFuture.get(2, TimeUnit.SECONDS);
        assertEquals(List.of(1, 2), processed);

        producerPool.shutdown();
        consumerPool.shutdown();
        assertTrue(producerPool.awaitTermination(2, TimeUnit.SECONDS));
        assertTrue(consumerPool.awaitTermination(2, TimeUnit.SECONDS));
    }
}
