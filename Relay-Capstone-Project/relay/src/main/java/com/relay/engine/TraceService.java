package com.relay.engine;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.relay.domain.Trace;
import com.relay.persistence.TraceRepository;
import org.springframework.stereotype.Service;

import java.util.UUID;

@Service
public class TraceService {

    private final TraceRepository repo;
    private final ObjectMapper mapper;

    public TraceService(TraceRepository repo, ObjectMapper mapper) {
        this.repo = repo;
        this.mapper = mapper;
    }

    public void record(UUID runId, String nodeId, String kind, JsonNode detail) {
        Trace t = new Trace();
        t.setRunId(runId);
        t.setNodeId(nodeId);
        t.setKind(kind);
        try {
            t.setDetail(mapper.writeValueAsString(detail == null ? mapper.createObjectNode() : detail));
        } catch (Exception e) {
            t.setDetail("{}");
        }
        repo.save(t);
    }
}
