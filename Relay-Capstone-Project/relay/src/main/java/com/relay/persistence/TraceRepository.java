package com.relay.persistence;

import com.relay.domain.Trace;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface TraceRepository extends JpaRepository<Trace, UUID> {

    List<Trace> findByRunIdOrderByCreatedAt(UUID runId);
}
