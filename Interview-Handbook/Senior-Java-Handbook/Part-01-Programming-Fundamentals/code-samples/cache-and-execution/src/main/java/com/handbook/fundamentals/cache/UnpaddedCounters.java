package com.handbook.fundamentals.cache;

/**
 * THE BUG — a performance bug, not a correctness bug. Each thread
 * increments its own dedicated slot in a shared {@code long[]}, so there is
 * no data race: every index is written by exactly one thread, and
 * {@link Thread#join()} establishes the happens-before edge needed for the
 * main thread to safely read final values afterward.
 *
 * <p>Despite that, this is slow under concurrent access from multiple
 * cores: adjacent {@code long} slots (8 bytes each) pack into the same
 * 64-byte CPU cache line, so when core A writes {@code counters[0]}, the
 * cache-coherency protocol (MESI/MESIF) invalidates that entire cache line
 * on every OTHER core holding it — including core B, which was about to
 * write the unrelated {@code counters[1]} sharing that same line. Each core
 * ping-pongs the line back and forth, even though the two threads never
 * touch each other's data. This is <b>false sharing</b>.
 *
 * @see PaddedCounters for the fix.
 */
public final class UnpaddedCounters {

    private final long[] counters;

    public UnpaddedCounters(int numCounters) {
        this.counters = new long[numCounters];
    }

    public void incrementNTimes(int index, long times) {
        for (long i = 0; i < times; i++) {
            counters[index]++;
        }
    }

    public long get(int index) {
        return counters[index];
    }
}
