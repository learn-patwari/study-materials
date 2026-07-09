package com.handbook.fundamentals.patterns.builder;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * THE FIX for the telescoping-constructor problem: a config object with 2
 * required fields (host, port) and 5 optional ones (timeouts, retries,
 * TLS, headers) would need either one constructor per meaningful
 * combination (telescoping) or a single constructor with 7 positional
 * parameters (unreadable and error-prone at call sites — which int is
 * which timeout?). The Builder pattern fixes both: required fields are
 * captured up front, optional fields are set via clearly-named methods in
 * any order, and the object is only ever exposed once fully, validly
 * constructed.
 */
public final class ServiceClientConfig {

    private final String host;
    private final int port;
    private final int connectTimeoutMillis;
    private final int readTimeoutMillis;
    private final int maxRetries;
    private final boolean useTls;
    private final Map<String, String> defaultHeaders;

    private ServiceClientConfig(Builder builder) {
        this.host = builder.host;
        this.port = builder.port;
        this.connectTimeoutMillis = builder.connectTimeoutMillis;
        this.readTimeoutMillis = builder.readTimeoutMillis;
        this.maxRetries = builder.maxRetries;
        this.useTls = builder.useTls;
        this.defaultHeaders = Map.copyOf(builder.defaultHeaders);
    }

    public String host() {
        return host;
    }

    public int port() {
        return port;
    }

    public int connectTimeoutMillis() {
        return connectTimeoutMillis;
    }

    public int readTimeoutMillis() {
        return readTimeoutMillis;
    }

    public int maxRetries() {
        return maxRetries;
    }

    public boolean useTls() {
        return useTls;
    }

    public Map<String, String> defaultHeaders() {
        return defaultHeaders;
    }

    public static Builder builder(String host, int port) {
        return new Builder(host, port);
    }

    public static final class Builder {
        private final String host;
        private final int port;
        private int connectTimeoutMillis = 5_000;
        private int readTimeoutMillis = 10_000;
        private int maxRetries = 0;
        private boolean useTls = false;
        private final Map<String, String> defaultHeaders = new LinkedHashMap<>();

        private Builder(String host, int port) {
            if (host == null || host.isBlank()) {
                throw new IllegalArgumentException("host must not be blank");
            }
            if (port <= 0 || port > 65535) {
                throw new IllegalArgumentException("port must be between 1 and 65535: " + port);
            }
            this.host = host;
            this.port = port;
        }

        public Builder connectTimeoutMillis(int millis) {
            if (millis <= 0) {
                throw new IllegalArgumentException("connectTimeoutMillis must be positive: " + millis);
            }
            this.connectTimeoutMillis = millis;
            return this;
        }

        public Builder readTimeoutMillis(int millis) {
            if (millis <= 0) {
                throw new IllegalArgumentException("readTimeoutMillis must be positive: " + millis);
            }
            this.readTimeoutMillis = millis;
            return this;
        }

        public Builder maxRetries(int retries) {
            if (retries < 0) {
                throw new IllegalArgumentException("maxRetries must not be negative: " + retries);
            }
            this.maxRetries = retries;
            return this;
        }

        public Builder useTls(boolean useTls) {
            this.useTls = useTls;
            return this;
        }

        public Builder header(String name, String value) {
            if (name == null || name.isBlank()) {
                throw new IllegalArgumentException("header name must not be blank");
            }
            defaultHeaders.put(name, value);
            return this;
        }

        public ServiceClientConfig build() {
            return new ServiceClientConfig(this);
        }
    }
}
