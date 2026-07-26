package com.relay.persistence;

import com.relay.domain.OutboxMessage;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.OffsetDateTime;

public interface OutboxRepository extends JpaRepository<OutboxMessage, Long> {

    /**
     * Claim one ready message id using {@code FOR UPDATE SKIP LOCKED} so many workers
     * pull disjoint rows without blocking. Returns null when nothing is ready.
     */
    @Query(value = """
            SELECT id FROM outbox
            WHERE status = 'READY' AND available_at <= :now
            ORDER BY id
            FOR UPDATE SKIP LOCKED
            LIMIT 1
            """, nativeQuery = true)
    Long claimReadyId(@Param("now") OffsetDateTime now);

    /**
     * Reaper: reset messages whose lease expired (worker crashed after locking but
     * before committing) back to available. In v1 a rolled-back transaction already
     * leaves status READY; this covers any lock/lease bookkeeping.
     */
    @Modifying
    @Query(value = """
            UPDATE outbox SET locked_by = NULL, locked_at = NULL
            WHERE status = 'READY' AND locked_at IS NOT NULL AND locked_at < :cutoff
            """, nativeQuery = true)
    int reapExpiredLeases(@Param("cutoff") OffsetDateTime cutoff);
}
