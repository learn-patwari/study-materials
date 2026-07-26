package com.relay.nodes;

/** Strategy for executing a single node type. Register a bean per type. */
public interface NodeExecutor {

    /** The node {@code type} this executor handles, e.g. "http_request". */
    String type();

    /** Whether this node performs an external side effect (must be idempotent). */
    default boolean sideEffecting() { return false; }

    NodeResult execute(NodeContext ctx);
}
