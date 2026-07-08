package com.handbook.interview;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;

/**
 * Classic "design a producer-consumer queue with graceful shutdown"
 * whiteboard problem. {@link BlockingQueue} already solves the
 * bounded-buffer / backpressure / wait-notify plumbing (this is the answer
 * to "why not hand-roll wait/notify yourself" -- {@code BlockingQueue} is
 * the standard-library primitive built exactly for this, and reimplementing
 * it with raw {@code wait()}/{@code notify()} is what actually gets asked
 * of candidates who claim they'd "just use a BlockingQueue" without
 * understanding what it saves them from getting wrong).
 *
 * <p>The interesting part interviewers actually probe is graceful shutdown:
 * a consumer blocked in {@code queue.take()} cannot be told "stop" by
 * simply setting a boolean flag, because it's parked and not polling
 * anything. The standard fix is a sentinel/"poison pill" value that,
 * when dequeued, tells the consumer to exit its loop instead of processing
 * it as real work.
 */
public final class PoisonPillWorkQueue<T> {

    private static final Object POISON_PILL = new Object();

    private final BlockingQueue<Object> queue;

    public PoisonPillWorkQueue(int capacity) {
        this.queue = new LinkedBlockingQueue<>(capacity);
    }

    /** Blocks if the queue is at capacity -- this IS the backpressure mechanism. */
    public void produce(T item) throws InterruptedException {
        queue.put(item);
    }

    public void shutdown() throws InterruptedException {
        queue.put(POISON_PILL);
    }

    /**
     * Consumes until the poison pill is seen, returning every real item
     * processed. In production this would be an infinite loop dispatching
     * to a handler; a bounded, return-a-list version is used here purely to
     * keep the drill's test deterministic and finite.
     */
    @SuppressWarnings("unchecked")
    public List<T> consumeUntilShutdown() throws InterruptedException {
        List<T> processed = new ArrayList<>();
        while (true) {
            Object item = queue.take();
            if (item == POISON_PILL) {
                return processed;
            }
            processed.add((T) item);
        }
    }
}
