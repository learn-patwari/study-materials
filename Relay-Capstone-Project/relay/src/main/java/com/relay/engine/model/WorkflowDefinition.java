package com.relay.engine.model;

import java.util.Map;

/** Parsed form of a workflow version's {@code definition} JSON. */
public class WorkflowDefinition {
    public String start;
    public Map<String, NodeDef> nodes;

    public NodeDef node(String id) {
        return nodes == null ? null : nodes.get(id);
    }
}
