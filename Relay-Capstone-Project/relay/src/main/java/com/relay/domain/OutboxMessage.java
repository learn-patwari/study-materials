package com.relay.domain;

import jakarta.persistence.*;
import java.time.OffsetDateTime;
import java.util.UUID;

/**
 * A durable queue message telling a worker to advance a run. Inserted in the same
 * transaction as the state change that produced it (transactional outbox).
 */
@Entity
@Table(name = "outbox")
public class OutboxMessage {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "run_id", nullable = false)
    private UUID runId;

    @Column(name = "available_at", nullable = false)
    private OffsetDateTime availableAt = OffsetDateTime.now();

    @Column(name = "locked_by")
    private String lockedBy;

    @Column(name = "locked_at")
    private OffsetDateTime lockedAt;

    @Column(nullable = false)
    private String status = "READY";

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public UUID getRunId() { return runId; }
    public void setRunId(UUID runId) { this.runId = runId; }

    public OffsetDateTime getAvailableAt() { return availableAt; }
    public void setAvailableAt(OffsetDateTime availableAt) { this.availableAt = availableAt; }

    public String getLockedBy() { return lockedBy; }
    public void setLockedBy(String lockedBy) { this.lockedBy = lockedBy; }

    public OffsetDateTime getLockedAt() { return lockedAt; }
    public void setLockedAt(OffsetDateTime lockedAt) { this.lockedAt = lockedAt; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
}
