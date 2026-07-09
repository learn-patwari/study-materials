package com.handbook.fundamentals.complexity;

import java.util.HashSet;
import java.util.Set;

/**
 * O(1)-average membership check via a {@link HashSet} (hash table under
 * the hood). Pays a fixed per-operation hashing cost regardless of
 * collection size, in exchange for no cache-friendly linear scan and
 * (amortized) extra memory overhead versus a plain array/list of the same
 * elements.
 *
 * @see ListLookup for the O(n) alternative and its trade-offs.
 */
public final class HashLookup {

    private final Set<Integer> values = new HashSet<>();

    public void add(int value) {
        values.add(value);
    }

    public boolean contains(int value) {
        return values.contains(value); // O(1) average: hash + bucket lookup
    }

    public int size() {
        return values.size();
    }
}
