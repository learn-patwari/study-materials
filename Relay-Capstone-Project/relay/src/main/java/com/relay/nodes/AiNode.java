package com.relay.nodes;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.fasterxml.jackson.databind.node.TextNode;
import com.relay.ai.LlmProvider;
import com.relay.ai.LlmRequest;
import com.relay.ai.LlmResponse;
import com.relay.ai.SchemaValidator;
import com.relay.engine.IdempotencyService;
import com.relay.engine.TraceService;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * AI node: calls the LLM provider, then validates the output against the node's
 * {@code outputSchema} (JSON Schema). Only schema-valid, typed output flows downstream —
 * the AI produces data, never authority (see 05-Node-Executors.md §5.2, 10-Hard-Problems.md).
 * The call is recorded via the idempotency ledger so a redelivery replays instead of re-calling.
 */
@Component
public class AiNode implements NodeExecutor {

    private final IdempotencyService idempotency;
    private final LlmProvider provider;
    private final SchemaValidator schemaValidator;
    private final TraceService traces;

    public AiNode(IdempotencyService idempotency, LlmProvider provider,
                  SchemaValidator schemaValidator, TraceService traces) {
        this.idempotency = idempotency;
        this.provider = provider;
        this.schemaValidator = schemaValidator;
        this.traces = traces;
    }

    @Override public String type() { return "ai"; }
    @Override public boolean sideEffecting() { return true; }

    @Override
    public NodeResult execute(NodeContext ctx) {
        ObjectMapper mapper = ctx.mapper();
        String prompt = ctx.configText("prompt", "");
        JsonNode schema = ctx.config() == null ? null : ctx.config().get("outputSchema");

        JsonNode call = idempotency.execute(ctx.runId(), ctx.nodeId(), "llm", () -> {
            LlmResponse r = provider.complete(new LlmRequest(prompt));
            JsonNode parsed;
            try {
                parsed = mapper.readTree(r.content());
            } catch (Exception e) {
                parsed = TextNode.valueOf(r.content());   // non-JSON output
            }
            ObjectNode res = mapper.createObjectNode();
            res.set("output", parsed);
            ObjectNode usage = mapper.createObjectNode();
            usage.put("promptTokens", r.promptTokens());
            usage.put("completionTokens", r.completionTokens());
            res.set("usage", usage);
            return res;
        });

        JsonNode output = call.get("output");

        ObjectNode detail = mapper.createObjectNode();
        detail.set("usage", call.get("usage"));
        detail.put("schemaEnforced", schema != null && !schema.isNull());
        traces.record(ctx.runId(), ctx.nodeId(), "LLM_CALL", detail);

        if (schema != null && !schema.isNull()) {
            List<String> issues = schemaValidator.validate(schema, output);
            if (!issues.isEmpty()) {
                throw new IllegalStateException("AI output failed schema validation: " + issues);
            }
        }
        return NodeResult.of(output);
    }
}
