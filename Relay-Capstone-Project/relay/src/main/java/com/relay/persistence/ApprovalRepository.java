package com.relay.persistence;

import com.relay.domain.Approval;
import com.relay.domain.ApprovalStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface ApprovalRepository extends JpaRepository<Approval, UUID> {

    Optional<Approval> findByRunIdAndNodeId(UUID runId, String nodeId);

    Optional<Approval> findByRunIdAndNodeIdAndStatus(UUID runId, String nodeId, ApprovalStatus status);

    List<Approval> findByStatusOrderByCreatedAt(ApprovalStatus status);
}
