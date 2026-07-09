package com.handbook.fundamentals.patterns.decorator;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

/**
 * The base implementation -- stands in for a real database-backed
 * repository. Tracks {@link #callCount()} purely so this chapter's tests
 * can PROVE the caching decorator actually reduces calls to this class,
 * not just assert that it does.
 */
public final class InMemoryUserRepository implements UserRepository {

    private final Map<String, String> data;
    private int callCount = 0;

    public InMemoryUserRepository(Map<String, String> data) {
        this.data = new HashMap<>(data);
    }

    @Override
    public Optional<String> findById(String id) {
        callCount++;
        return Optional.ofNullable(data.get(id));
    }

    public int callCount() {
        return callCount;
    }
}
