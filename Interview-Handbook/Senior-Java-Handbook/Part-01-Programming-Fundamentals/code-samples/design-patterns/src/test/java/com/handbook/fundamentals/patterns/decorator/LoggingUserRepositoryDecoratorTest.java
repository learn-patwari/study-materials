package com.handbook.fundamentals.patterns.decorator;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class LoggingUserRepositoryDecoratorTest {

    @Test
    void passesThroughCorrectResultWhileRecordingALogEntry() {
        InMemoryUserRepository base = new InMemoryUserRepository(Map.of("u1", "Alice"));
        LoggingUserRepositoryDecorator logging = new LoggingUserRepositoryDecorator(base);

        Optional<String> result = logging.findById("u1");

        assertEquals(Optional.of("Alice"), result, "decorator must not alter the underlying result");
        assertEquals(List.of("findById(u1)", "  -> found"), logging.log());
    }

    @Test
    void logsAMissDistinctlyFromAHit() {
        InMemoryUserRepository base = new InMemoryUserRepository(Map.of());
        LoggingUserRepositoryDecorator logging = new LoggingUserRepositoryDecorator(base);

        logging.findById("missing");

        assertEquals(List.of("findById(missing)", "  -> not found"), logging.log());
    }

    @Test
    void composesWithCachingDecorator() {
        InMemoryUserRepository base = new InMemoryUserRepository(Map.of("u1", "Alice"));
        CachingUserRepositoryDecorator cached = new CachingUserRepositoryDecorator(base);
        LoggingUserRepositoryDecorator logged = new LoggingUserRepositoryDecorator(cached);

        logged.findById("u1");
        logged.findById("u1"); // should hit the cache, but STILL be logged each time

        assertEquals(Optional.of("Alice"), logged.findById("u1"));
        assertEquals(1, base.callCount(), "caching decorator underneath must still only delegate once");
        assertEquals(6, logged.log().size(), "logging decorator must record all 3 calls, cached or not");
    }
}
