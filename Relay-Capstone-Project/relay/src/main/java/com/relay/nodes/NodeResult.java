package com.relay.nodes;

import com.fasterxml.jackson.databind.JsonNode;

/**
 * Result of executing one node. {@code branchResult} is non-null only for condition
 * nodes, telling the engine which branch (onTrue/onFalse) to follow.
 */
public record NodeResult(JsonNode output, Boolean branchResult) {

    public static NodeResult of(JsonNode output) {
        return new NodeResult(output, null);
    }

    public static NodeResult branch(JsonNode output, boolean branchResult) {
        return new NodeResult(output, branchResult);
    }
}
