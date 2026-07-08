package com.handbook.urlshortener;

import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Repository;

/**
 * In-memory stand-in for the real cache-aside pair described in this
 * chapter's Architecture section: a Redis lookup on the read path (code -&gt;
 * long URL) backed by a durable primary store (e.g. a sharded relational
 * table keyed by the same short code) on a cache miss. A single
 * {@link ConcurrentHashMap} plays both roles here so the code sample stays
 * dependency-free and testable offline; production sizing/TTL/eviction
 * concerns for the real Redis layer are covered in Production Examples.
 */
@Repository
public class UrlRepository {

    private final ConcurrentHashMap<String, String> codeToLongUrl = new ConcurrentHashMap<>();

    public void save(String code, String longUrl) {
        codeToLongUrl.put(code, longUrl);
    }

    public Optional<String> findLongUrl(String code) {
        return Optional.ofNullable(codeToLongUrl.get(code));
    }

    public boolean exists(String code) {
        return codeToLongUrl.containsKey(code);
    }
}
