package com.relay.persistence;

import com.relay.domain.Step;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface StepRepository extends JpaRepository<Step, UUID> {

    List<Step> findByRunIdOrderByStartedAt(UUID runId);

    int countByRunIdAndNodeId(UUID runId, String nodeId);
}
