package com.handbook.jvm;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Proves the fix actually bounds memory: inserting far more entries than the
 * configured capacity must never grow the cache past that capacity, and the
 * least-recently-used key must be the one evicted.
 */
class BoundedRequestCacheTest {

    @Test
    void neverGrowsPastConfiguredCapacity() {
        BoundedRequestCache cache = new BoundedRequestCache(100);

        for (int i = 0; i < 10_000; i++) {
            cache.put("key-" + i);
        }

        assertEquals(100, cache.size(),
                "cache must stay bounded regardless of how many distinct keys are inserted");
    }

    @Test
    void evictsLeastRecentlyUsedFirst() {
        BoundedRequestCache cache = new BoundedRequestCache(2);

        cache.put("a");
        cache.put("b");
        cache.contains("a"); // touch "a" so "b" becomes the LRU entry
        cache.put("c");      // capacity 2 exceeded -> evict LRU ("b")

        assertTrue(cache.contains("a"), "recently-touched entry should survive eviction");
        assertFalse(cache.contains("b"), "least-recently-used entry should be evicted");
        assertTrue(cache.contains("c"), "newly-inserted entry should be present");
    }

    @Test
    void unboundedCacheDemonstratesTheBugForComparison() {
        UnboundedRequestCache buggy = new UnboundedRequestCache();
        for (int i = 0; i < 10_000; i++) {
            buggy.put("key-" + i);
        }
        // Documents the failure mode this chapter is about: with no eviction
        // policy at all, cache size is unbounded by construction.
        assertEquals(10_000, buggy.size(),
                "UnboundedRequestCache has no eviction — this is the bug, not a bound to preserve");
    }
}
