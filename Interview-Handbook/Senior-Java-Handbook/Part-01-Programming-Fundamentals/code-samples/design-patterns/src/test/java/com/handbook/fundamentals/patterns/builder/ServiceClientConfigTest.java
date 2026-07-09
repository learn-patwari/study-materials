package com.handbook.fundamentals.patterns.builder;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ServiceClientConfigTest {

    @Test
    void requiredFieldsOnlyProducesSensibleDefaults() {
        ServiceClientConfig config = ServiceClientConfig.builder("api.example.com", 443).build();

        assertEquals("api.example.com", config.host());
        assertEquals(443, config.port());
        assertEquals(5_000, config.connectTimeoutMillis());
        assertEquals(10_000, config.readTimeoutMillis());
        assertEquals(0, config.maxRetries());
        assertFalse(config.useTls());
        assertTrue(config.defaultHeaders().isEmpty());
    }

    @Test
    void allOptionalFieldsCanBeSetInAnyOrder() {
        ServiceClientConfig config = ServiceClientConfig.builder("internal-api", 8443)
                .useTls(true)
                .maxRetries(3)
                .header("X-Request-Source", "handbook")
                .connectTimeoutMillis(2_000)
                .readTimeoutMillis(15_000)
                .header("Accept", "application/json")
                .build();

        assertEquals("internal-api", config.host());
        assertEquals(8443, config.port());
        assertEquals(2_000, config.connectTimeoutMillis());
        assertEquals(15_000, config.readTimeoutMillis());
        assertEquals(3, config.maxRetries());
        assertTrue(config.useTls());
        assertEquals("handbook", config.defaultHeaders().get("X-Request-Source"));
        assertEquals("application/json", config.defaultHeaders().get("Accept"));
    }

    @Test
    void rejectsBlankHost() {
        assertThrows(IllegalArgumentException.class, () -> ServiceClientConfig.builder("  ", 80));
    }

    @Test
    void rejectsOutOfRangePort() {
        assertThrows(IllegalArgumentException.class, () -> ServiceClientConfig.builder("host", 0));
        assertThrows(IllegalArgumentException.class, () -> ServiceClientConfig.builder("host", 70_000));
    }

    @Test
    void rejectsNonPositiveTimeouts() {
        ServiceClientConfig.Builder builder = ServiceClientConfig.builder("host", 80);
        assertThrows(IllegalArgumentException.class, () -> builder.connectTimeoutMillis(0));
        assertThrows(IllegalArgumentException.class, () -> builder.readTimeoutMillis(-1));
    }

    @Test
    void rejectsNegativeRetries() {
        ServiceClientConfig.Builder builder = ServiceClientConfig.builder("host", 80);
        assertThrows(IllegalArgumentException.class, () -> builder.maxRetries(-1));
    }
}
