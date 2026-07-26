package com.relay.nodes;

import com.fasterxml.jackson.databind.JsonNode;
import com.relay.engine.IdempotencyService;
import com.relay.external.MockExternalWorld;
import org.springframework.stereotype.Component;

/** Deterministic, side-effecting node: sends a (mocked) notification, exactly once. */
@Component
public class NotifyNode implements NodeExecutor {

    private final IdempotencyService idempotency;
    private final MockExternalWorld world;

    public NotifyNode(IdempotencyService idempotency, MockExternalWorld world) {
        this.idempotency = idempotency;
        this.world = world;
    }

    @Override public String type() { return "notify"; }
    @Override public boolean sideEffecting() { return true; }

    @Override
    public NodeResult execute(NodeContext ctx) {
        String to = ctx.configText("to", "ops");
        String message = ctx.configText("template", "");
        String key = ctx.idempotencyKey("notify");
        JsonNode result = idempotency.execute(ctx.runId(), ctx.nodeId(), "notify",
                () -> world.notify(key, to, message));
        return NodeResult.of(result);
    }
}
