package com.handbook.interview;

/**
 * Classic "design a rate limiter" whiteboard problem, implemented with the
 * token bucket algorithm: capacity tokens refill continuously at
 * {@code refillTokensPerSecond}, a request is allowed iff at least one
 * token is available at call time, and each allowed request consumes one
 * token.
 *
 * <p>Deliberately lock-based rather than lock-free/CAS-looped: the refill
 * calculation (elapsed time * rate, clamped to capacity) and the
 * consume-a-token decision must be observed atomically together, or two
 * threads racing on a lock-free {@code compareAndSet} could each read the
 * same stale token count and both decide "allowed" when only one token was
 * actually available -- this is the follow-up an interviewer expects you to
 * volunteer, not wait to be asked.
 */
public final class TokenBucketRateLimiter {

    private final long capacity;
    private final double refillTokensPerSecond;
    private final Object lock = new Object();

    private double availableTokens;
    private long lastRefillNanos;

    public TokenBucketRateLimiter(long capacity, double refillTokensPerSecond) {
        this(capacity, refillTokensPerSecond, System.nanoTime());
    }

    /** Package-private constructor for deterministic testing with a fake clock. */
    TokenBucketRateLimiter(long capacity, double refillTokensPerSecond, long nowNanos) {
        if (capacity <= 0) {
            throw new IllegalArgumentException("capacity must be positive");
        }
        if (refillTokensPerSecond <= 0) {
            throw new IllegalArgumentException("refillTokensPerSecond must be positive");
        }
        this.capacity = capacity;
        this.refillTokensPerSecond = refillTokensPerSecond;
        this.availableTokens = capacity;
        this.lastRefillNanos = nowNanos;
    }

    public boolean tryAcquire() {
        return tryAcquire(System.nanoTime());
    }

    /** Package-private overload for deterministic testing with a fake clock. */
    boolean tryAcquire(long nowNanos) {
        synchronized (lock) {
            refill(nowNanos);
            if (availableTokens >= 1.0) {
                availableTokens -= 1.0;
                return true;
            }
            return false;
        }
    }

    private void refill(long nowNanos) {
        long elapsedNanos = nowNanos - lastRefillNanos;
        if (elapsedNanos <= 0) {
            return;
        }
        double elapsedSeconds = elapsedNanos / 1_000_000_000.0;
        double refilled = elapsedSeconds * refillTokensPerSecond;
        availableTokens = Math.min(capacity, availableTokens + refilled);
        lastRefillNanos = nowNanos;
    }
}
