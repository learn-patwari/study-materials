package com.relay.nodes;

import com.fasterxml.jackson.databind.JsonNode;
import com.relay.engine.IdempotencyService;
import com.relay.external.MockExternalWorld;
import org.springframework.stereotype.Component;

/** Deterministic, side-effecting node: performs a (mocked) HTTP call, exactly once. */
@Component
public class HttpRequestNode implements NodeExecutor {

    private final IdempotencyService idempotency;
    private final MockExternalWorld world;

    public HttpRequestNode(IdempotencyService idempotency, MockExternalWorld world) {
        this.idempotency = idempotency;
        this.world = world;
    }

    @Override public String type() { return "http_request"; }
    @Override public boolean sideEffecting() { return true; }

    @Override
    public NodeResult execute(NodeContext ctx) {
        String method = ctx.configText("method", "GET");
        String url = ctx.configText("url", "");
        JsonNode body = ctx.config() == null ? null : ctx.config().get("body");
        String key = ctx.idempotencyKey("call");
        JsonNode result = idempotency.execute(ctx.runId(), ctx.nodeId(), "call",
                () -> world.http(key, method, url, body));
        return NodeResult.of(result);
    }
}
