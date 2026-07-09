package com.handbook.fundamentals.patterns.decorator;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

/**
 * Adds caching to ANY {@link UserRepository} implementation without
 * modifying it — the base class ({@code InMemoryUserRepository}, or a
 * real database-backed one) has no idea this decorator exists. This is
 * the Open/Closed Principle applied to cross-cutting concerns: caching is
 * added by composition, not by editing the base repository's source.
 */
public final class CachingUserRepositoryDecorator implements UserRepository {

    private final UserRepository delegate;
    private final Map<String, Optional<String>> cache = new HashMap<>();

    public CachingUserRepositoryDecorator(UserRepository delegate) {
        this.delegate = delegate;
    }

    @Override
    public Optional<String> findById(String id) {
        return cache.computeIfAbsent(id, delegate::findById);
    }
}
