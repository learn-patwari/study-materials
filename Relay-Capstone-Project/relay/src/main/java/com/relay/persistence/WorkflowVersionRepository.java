package com.relay.persistence;

import com.relay.domain.WorkflowVersion;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface WorkflowVersionRepository extends JpaRepository<WorkflowVersion, UUID> {

    List<WorkflowVersion> findByWorkflowIdOrderByVersionDesc(UUID workflowId);

    Optional<WorkflowVersion> findByWorkflowIdAndVersion(UUID workflowId, int version);
}
