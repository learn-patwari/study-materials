package com.relay.nodes;

import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.stereotype.Component;

/**
 * Non-side-effecting node. The delay itself is realized by the engine scheduling the
 * NEXT message with a future {@code available_at}; this executor just records the intent.
 */
@Component
public class DelayNode implements NodeExecutor {

    @Override public String type() { return "delay"; }

    @Override
    public NodeResult execute(NodeContext ctx) {
        long ms = ctx.configLong("durationMs", 0);
        ObjectNode output = ctx.mapper().createObjectNode();
        output.put("delayedMs", ms);
        return NodeResult.of(output);
    }
}
