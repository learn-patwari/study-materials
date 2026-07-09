package com.handbook.fundamentals.patterns.decorator;

import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class CachingUserRepositoryDecoratorTest {

    @Test
    void firstLookupDelegatesButSecondLookupHitsTheCacheInstead() {
        InMemoryUserRepository base = new InMemoryUserRepository(Map.of("u1", "Alice"));
        CachingUserRepositoryDecorator cached = new CachingUserRepositoryDecorator(base);

        Optional<String> first = cached.findById("u1");
        Optional<String> second = cached.findById("u1");
        Optional<String> third = cached.findById("u1");

        assertEquals(Optional.of("Alice"), first);
        assertEquals(Optional.of("Alice"), second);
        assertEquals(Optional.of("Alice"), third);
        // THE proof the decorator does what it claims: 3 logical lookups,
        // but the underlying repository was only ever actually called once.
        assertEquals(1, base.callCount(),
                "second and third lookups must be served from cache, not delegate again");
    }

    @Test
    void differentKeysEachDelegateOnceIndependently() {
        InMemoryUserRepository base = new InMemoryUserRepository(Map.of("u1", "Alice", "u2", "Bob"));
        CachingUserRepositoryDecorator cached = new CachingUserRepositoryDecorator(base);

        cached.findById("u1");
        cached.findById("u2");
        cached.findById("u1");
        cached.findById("u2");

        assertEquals(2, base.callCount(), "two distinct keys should each delegate exactly once");
    }

    @Test
    void cachesAbsentResultsTooNotJustPresentOnes() {
        InMemoryUserRepository base = new InMemoryUserRepository(Map.of());
        CachingUserRepositoryDecorator cached = new CachingUserRepositoryDecorator(base);

        assertTrue(cached.findById("missing").isEmpty());
        assertTrue(cached.findById("missing").isEmpty());

        assertEquals(1, base.callCount(), "a cached miss must not re-delegate on the next lookup");
    }
}
