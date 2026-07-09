package com.handbook.fundamentals.cache;

/**
 * THE FIX for {@link UnpaddedCounters}: pad each counter out to its own
 * 64-byte cache line so no two threads' counters can ever share one.
 *
 * <p>Rather than relying on a padded <em>object's</em> field layout (the
 * JVM is free to reorder fields for alignment/compactness, so hand-padding
 * a class with unused {@code long} fields before/after the real value is
 * not portably guaranteed to work), this uses a striped array: each logical
 * counter occupies every {@code STRIDE}-th slot, with the slots in between
 * left unused as padding. This is the same trick used by libraries like the
 * LMAX Disruptor for its {@code Sequence} counters, expressed at its
 * simplest.
 */
public final class PaddedCounters {

    /** 8 longs * 8 bytes = 64 bytes -- one typical x86/ARM cache line. */
    private static final int STRIDE = 8;

    private final long[] counters;

    public PaddedCounters(int numCounters) {
        this.counters = new long[numCounters * STRIDE];
    }

    public void incrementNTimes(int index, long times) {
        int slot = index * STRIDE;
        for (long i = 0; i < times; i++) {
            counters[slot]++;
        }
    }

    public long get(int index) {
        return counters[index * STRIDE];
    }
}
