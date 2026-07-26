package com.relay.engine.model;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.NullNode;

/** A single node in a workflow definition. */
public class NodeDef {
    public String type;
    public String next;
    public String onTrue;
    public String onFalse;
    public boolean sensitive;
    public JsonNode config = NullNode.getInstance();

    public String type() { return type; }
    public boolean isBranching() { return "condition".equals(type); }
}
