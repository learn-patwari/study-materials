package com.handbook.interview;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class TokenBucketRateLimiterTest {

    @Test
    void allowsRequestsUpToCapacityThenBlocks() {
        long t0 = 0L;
        TokenBucketRateLimiter limiter = new TokenBucketRateLimiter(3, 1.0, t0);

        assertTrue(limiter.tryAcquire(t0), "1st request within capacity should be allowed");
        assertTrue(limiter.tryAcquire(t0), "2nd request within capacity should be allowed");
        assertTrue(limiter.tryAcquire(t0), "3rd request within capacity should be allowed");
        assertFalse(limiter.tryAcquire(t0), "4th request with no elapsed time should be denied");
    }

    @Test
    void refillsTokensProportionallyToElapsedTime() {
        long t0 = 0L;
        TokenBucketRateLimiter limiter = new TokenBucketRateLimiter(2, 1.0, t0); // 1 token/sec

        assertTrue(limiter.tryAcquire(t0));
        assertTrue(limiter.tryAcquire(t0));
        assertFalse(limiter.tryAcquire(t0), "bucket should be empty immediately after draining capacity");

        long t1 = t0 + 1_000_000_000L; // +1 second -> +1 token refilled
        assertTrue(limiter.tryAcquire(t1), "1 second elapsed at 1 token/sec should refill exactly 1 token");
        assertFalse(limiter.tryAcquire(t1), "only 1 token should have been refilled, not 2");
    }

    @Test
    void neverRefillsPastCapacity() {
        long t0 = 0L;
        TokenBucketRateLimiter limiter = new TokenBucketRateLimiter(2, 100.0, t0);

        long farFuture = t0 + 3_600_000_000_000L; // +1 hour, would be 360,000 tokens uncapped
        assertTrue(limiter.tryAcquire(farFuture));
        assertTrue(limiter.tryAcquire(farFuture));
        assertFalse(limiter.tryAcquire(farFuture), "bucket must never exceed configured capacity");
    }

    @Test
    void rejectsNonPositiveConfiguration() {
        org.junit.jupiter.api.Assertions.assertThrows(IllegalArgumentException.class,
                () -> new TokenBucketRateLimiter(0, 1.0));
        org.junit.jupiter.api.Assertions.assertThrows(IllegalArgumentException.class,
                () -> new TokenBucketRateLimiter(1, 0.0));
    }
}
