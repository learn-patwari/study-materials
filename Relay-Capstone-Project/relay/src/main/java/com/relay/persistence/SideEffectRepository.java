package com.relay.persistence;

import com.relay.domain.SideEffect;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;
import java.util.UUID;

public interface SideEffectRepository extends JpaRepository<SideEffect, UUID> {

    Optional<SideEffect> findByRunIdAndNodeIdAndAttemptKey(UUID runId, String nodeId, String attemptKey);
}
