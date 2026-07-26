package com.relay.engine;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.relay.domain.SideEffect;
import com.relay.persistence.SideEffectRepository;
import org.springframework.stereotype.Service;

import java.util.UUID;
import java.util.function.Supplier;

/**
 * Wraps a side-effecting action so it is recorded at most once per
 * (run, node, attemptKey). If a ledger row already exists, the stored result is
 * replayed instead of re-performing. Combined with the mocked world being idempotent
 * by key, this gives exactly-once side effects (see 05-Node-Executors.md §5.4).
 */
@Service
public class IdempotencyService {

    private final SideEffectRepository ledger;
    private final ObjectMapper mapper;

    public IdempotencyService(SideEffectRepository ledger, ObjectMapper mapper) {
        this.ledger = ledger;
        this.mapper = mapper;
    }

    public JsonNode execute(UUID runId, String nodeId, String attemptKey, Supplier<JsonNode> action) {
        return ledger.findByRunIdAndNodeIdAndAttemptKey(runId, nodeId, attemptKey)
                .map(this::replay)
                .orElseGet(() -> perform(runId, nodeId, attemptKey, action));
    }

    private JsonNode replay(SideEffect existing) {
        try {
            return existing.getResult() == null ? mapper.nullNode() : mapper.readTree(existing.getResult());
        } catch (Exception e) {
            throw new IllegalStateException("corrupt side-effect result", e);
        }
    }

    private JsonNode perform(UUID runId, String nodeId, String attemptKey, Supplier<JsonNode> action) {
        JsonNode result = action.get();                 // mocked world is idempotent by key
        SideEffect se = new SideEffect();
        se.setRunId(runId);
        se.setNodeId(nodeId);
        se.setAttemptKey(attemptKey);
        try {
            se.setResult(mapper.writeValueAsString(result));
        } catch (Exception e) {
            throw new IllegalStateException("cannot serialize side-effect result", e);
        }
        ledger.save(se);
        return result;
    }
}
