package com.relay.engine;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

/**
 * The worker loop. On each tick, drains the outbox queue by repeatedly claiming and
 * advancing runs until nothing is ready. Kept single-threaded for v1 correctness
 * simplicity; scale out by running more instances or a worker pool later.
 *
 * <p>Disabled with {@code relay.engine.enabled=false} so tests can drive the engine
 * deterministically via {@link OutboxProcessor}.
 */
@Service
@ConditionalOnProperty(name = "relay.engine.enabled", havingValue = "true", matchIfMissing = true)
public class WorkerService {

    private final OutboxProcessor processor;

    public WorkerService(OutboxProcessor processor) {
        this.processor = processor;
    }

    @Scheduled(fixedDelayString = "${relay.engine.poll-interval-ms:500}")
    public void poll() {
        int guard = 0;
        // Each iteration is its own transaction (per-node atomicity).
        while (processor.claimAndAdvanceOne() && guard++ < 1000) {
            // keep draining
        }
    }
}
