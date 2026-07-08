package com.handbook.jvm;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * THE BUG. A request/response cache that never evicts anything.
 *
 * <p>This is a distilled version of a real production incident pattern:
 * a per-request cache (e.g. "dedupe identical downstream calls within a
 * request batch") that someone made a singleton/static field "to avoid
 * re-creating it," so entries from every request pile up for the life of
 * the JVM. Under a steady request rate this produces the classic
 * <b>slow memory leak</b> signature: heap usage climbs across every GC
 * cycle instead of returning to baseline, eventually ending in
 * {@code OutOfMemoryError} in a bare JVM or an {@code OOMKilled} pod
 * eviction under Kubernetes (see the chapter's Production Troubleshooting
 * section for the full runbook on telling this apart from a legitimate
 * working-set increase).
 *
 * @see BoundedRequestCache for the fix.
 */
public final class UnboundedRequestCache {

    private final Map<String, byte[]> cache = new ConcurrentHashMap<>();

    /** Simulates caching a ~4 KB response body per unique key. Never evicts. */
    public void put(String key) {
        cache.put(key, new byte[4096]);
    }

    public int size() {
        return cache.size();
    }
}
