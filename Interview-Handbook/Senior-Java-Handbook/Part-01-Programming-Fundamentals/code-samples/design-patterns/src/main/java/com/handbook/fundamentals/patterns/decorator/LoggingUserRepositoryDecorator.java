package com.handbook.fundamentals.patterns.decorator;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

/**
 * Adds logging to ANY {@link UserRepository} implementation without
 * modifying it. Composable with {@link CachingUserRepositoryDecorator} --
 * decorators wrapping decorators wrapping a base implementation is the
 * core of why this pattern avoids the subclass explosion a naive
 * "CachingLoggingUserRepository extends UserRepositoryImpl" approach
 * would produce for every combination of cross-cutting concerns.
 */
public final class LoggingUserRepositoryDecorator implements UserRepository {

    private final UserRepository delegate;
    private final List<String> log = new ArrayList<>();

    public LoggingUserRepositoryDecorator(UserRepository delegate) {
        this.delegate = delegate;
    }

    @Override
    public Optional<String> findById(String id) {
        log.add("findById(" + id + ")");
        Optional<String> result = delegate.findById(id);
        log.add("  -> " + (result.isPresent() ? "found" : "not found"));
        return result;
    }

    public List<String> log() {
        return List.copyOf(log);
    }
}
