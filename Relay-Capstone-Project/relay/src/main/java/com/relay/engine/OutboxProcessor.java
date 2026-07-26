package com.relay.engine;

import com.relay.domain.OutboxMessage;
import com.relay.persistence.OutboxRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;

/**
 * Claims one outbox message and advances its run by one node — all in a single
 * transaction. If the process dies mid-node, the transaction rolls back, the message
 * stays READY, and it is redelivered (at-least-once); idempotency keeps side effects
 * exactly-once. Separate bean so {@link Transactional} applies (no self-invocation).
 */
@Service
public class OutboxProcessor {

    private final OutboxRepository outbox;
    private final RunAdvancer advancer;
    private final String workerId = "worker-" + Long.toHexString(System.nanoTime());

    public OutboxProcessor(OutboxRepository outbox, RunAdvancer advancer) {
        this.outbox = outbox;
        this.advancer = advancer;
    }

    @Transactional
    public boolean claimAndAdvanceOne() {
        Long id = outbox.claimReadyId(OffsetDateTime.now());
        if (id == null) return false;
        OutboxMessage msg = outbox.findById(id).orElse(null);
        if (msg == null) return false;
        msg.setStatus("DONE");
        msg.setLockedBy(workerId);
        msg.setLockedAt(OffsetDateTime.now());
        outbox.save(msg);

        advancer.advanceOneNode(msg.getRunId());
        return true;
    }
}
