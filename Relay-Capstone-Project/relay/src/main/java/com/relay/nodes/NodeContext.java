package com.relay.nodes;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.UUID;

/** Everything a node executor needs: the run/node identity and template-resolved config. */
public record NodeContext(UUID runId, String nodeId, JsonNode config, ObjectMapper mapper) {

    public String configText(String field, String defaultValue) {
        JsonNode v = config == null ? null : config.get(field);
        return (v == null || v.isNull()) ? defaultValue : v.asText();
    }

    public long configLong(String field, long defaultValue) {
        JsonNode v = config == null ? null : config.get(field);
        return (v == null || v.isNull()) ? defaultValue : v.asLong();
    }

    /** Stable idempotency key for a side-effecting call from this node. */
    public String idempotencyKey(String action) {
        return runId + ":" + nodeId + ":" + action;
    }
}
