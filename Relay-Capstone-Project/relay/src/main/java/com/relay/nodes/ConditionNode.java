package com.relay.nodes;

import com.fasterxml.jackson.databind.node.ObjectNode;
import com.relay.engine.ConditionEvaluator;
import org.springframework.stereotype.Component;

/** Deterministic, non-side-effecting node: evaluates a boolean expr and picks a branch. */
@Component
public class ConditionNode implements NodeExecutor {

    private final ConditionEvaluator evaluator;

    public ConditionNode(ConditionEvaluator evaluator) {
        this.evaluator = evaluator;
    }

    @Override public String type() { return "condition"; }

    @Override
    public NodeResult execute(NodeContext ctx) {
        String expr = ctx.configText("expr", null);
        boolean result = evaluator.evaluate(expr);
        ObjectNode output = ctx.mapper().createObjectNode();
        output.put("expr", expr);
        output.put("result", result);
        return NodeResult.branch(output, result);
    }
}
