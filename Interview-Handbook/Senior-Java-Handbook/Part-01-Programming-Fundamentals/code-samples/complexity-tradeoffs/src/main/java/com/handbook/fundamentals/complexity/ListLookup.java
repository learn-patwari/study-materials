package com.handbook.fundamentals.complexity;

import java.util.ArrayList;
import java.util.List;

/**
 * O(n) membership check via a linear scan through an {@link ArrayList}.
 * Simple, cache-friendly for small collections (see Chapter 01.01 on why
 * contiguous-array scans are cheap per-element), but scales linearly with
 * collection size regardless of how many elements are actually being
 * looked up.
 *
 * @see HashLookup for the O(1)-average alternative.
 */
public final class ListLookup {

    private final List<Integer> values = new ArrayList<>();

    public void add(int value) {
        values.add(value);
    }

    public boolean contains(int value) {
        return values.contains(value); // O(n): ArrayList.contains() scans linearly
    }

    public int size() {
        return values.size();
    }
}
