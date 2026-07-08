package com.handbook.jvm;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * THE FIX for {@link UnboundedRequestCache}: a bounded, thread-safe
 * least-recently-used cache built on {@link LinkedHashMap}'s
 * access-order mode plus {@code removeEldestEntry}, which is the standard
 * JDK-only way to build an LRU cache without pulling in Caffeine/Guava for
 * something this simple.
 *
 * <p>Synchronizing every access looks heavy-handed, but {@code LinkedHashMap}
 * in access-order mode mutates its internal linked list on {@code get()} as
 * well as {@code put()} — it is <b>not</b> safe to wrap with a
 * read-write lock that allows concurrent reads. A plain {@code synchronized}
 * block is the correct, simplest fix; if this cache becomes a contention
 * hot spot under profiling, that is the point to reach for Caffeine
 * (segmented locking, per-entry TinyLFU eviction) rather than hand-rolling
 * a fancier lock here.
 */
public final class BoundedRequestCache {

    private final int maxEntries;
    private final Map<String, byte[]> cache;

    public BoundedRequestCache(int maxEntries) {
        this.maxEntries = maxEntries;
        // accessOrder=true turns this into an LRU (not insertion-order) list.
        this.cache = new LinkedHashMap<>(maxEntries, 0.75f, true) {
            @Override
            protected boolean removeEldestEntry(Map.Entry<String, byte[]> eldest) {
                return size() > BoundedRequestCache.this.maxEntries;
            }
        };
    }

    public synchronized void put(String key) {
        cache.put(key, new byte[4096]);
    }

    public synchronized boolean contains(String key) {
        // Must be get(), not containsKey(): access-order LinkedHashMap only
        // reorders its internal list on get(), so containsKey() would silently
        // fail to protect this key from the next eviction.
        return cache.get(key) != null;
    }

    public synchronized int size() {
        return cache.size();
    }
}
