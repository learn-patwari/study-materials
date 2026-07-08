package com.handbook.urlshortener;

import java.util.concurrent.atomic.AtomicLong;
import org.springframework.stereotype.Component;

/**
 * Simulates the "ticket server" / range-allocation pattern real URL
 * shorteners use to hand out globally unique IDs without a DB round trip
 * per request: each application instance periodically claims a contiguous
 * BLOCK of IDs (in production, via a single atomic
 * {@code UPDATE counters SET next_value = next_value + :blockSize ...
 * RETURNING next_value} against a small dedicated table, or an equivalent
 * distributed counter like a ZooKeeper/etcd sequence), then serves IDs out
 * of that block locally with a lock-free {@link AtomicLong} until it's
 * exhausted, at which point it claims the next block.
 *
 * <p>This keeps ID generation on the hot path lock-free and DB-free for
 * {@code blockSize - 1} out of every {@code blockSize} requests, at the
 * cost of "wasting" up to {@code blockSize - 1} IDs if an instance crashes
 * mid-block — an acceptable trade given the ID space (Base62, 7+ chars) has
 * enormous headroom.
 */
@Component
public final class RangeBasedIdGenerator {

    private final int blockSize;
    private final BlockAllocator blockAllocator;

    private final Object blockLock = new Object();
    private volatile long blockEnd = 0;      // exclusive upper bound of current block
    private final AtomicLong nextId = new AtomicLong(0);

    public RangeBasedIdGenerator() {
        this(1000, new InMemoryBlockAllocator());
    }

    /** Package-private constructor for testing with a small block size and a fake allocator. */
    RangeBasedIdGenerator(int blockSize, BlockAllocator blockAllocator) {
        if (blockSize <= 0) {
            throw new IllegalArgumentException("blockSize must be positive");
        }
        this.blockSize = blockSize;
        this.blockAllocator = blockAllocator;
    }

    public long nextId() {
        while (true) {
            long candidate = nextId.getAndIncrement();
            if (candidate < blockEnd) {
                return candidate;
            }
            claimNextBlock(candidate);
            // loop and retry against the freshly claimed block
        }
    }

    private void claimNextBlock(long observedExhaustedId) {
        synchronized (blockLock) {
            // Another thread may have already claimed a new block while we
            // were waiting on the lock — only claim if we're still exhausted.
            if (observedExhaustedId < blockEnd) {
                return;
            }
            long start = blockAllocator.claimBlockStart(blockSize);
            nextId.set(start);
            blockEnd = start + blockSize;
        }
    }

    /** Abstraction over "however the block start is actually allocated" (DB sequence, etcd, ...). */
    interface BlockAllocator {
        long claimBlockStart(int blockSize);
    }

    /** Standing in for the real DB-sequence-backed allocator in this offline code sample. */
    private static final class InMemoryBlockAllocator implements BlockAllocator {
        private final AtomicLong nextBlockStart = new AtomicLong(0);

        @Override
        public long claimBlockStart(int blockSize) {
            return nextBlockStart.getAndAdd(blockSize);
        }
    }
}
