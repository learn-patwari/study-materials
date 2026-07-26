package com.relay.engine;

/**
 * Thrown by a node when the failure is deterministic and must NOT be retried
 * (e.g., AI output failing schema validation). Transient failures throw ordinary
 * runtime exceptions and are retried with backoff.
 */
public class NonRetryableException extends RuntimeException {
    public NonRetryableException(String message) {
        super(message);
    }
}
