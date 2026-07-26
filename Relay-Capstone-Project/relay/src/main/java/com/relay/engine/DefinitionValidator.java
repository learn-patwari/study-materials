package com.relay.engine;

import com.relay.engine.model.NodeDef;
import com.relay.engine.model.WorkflowDefinition;
import org.springframework.stereotype.Component;

import java.util.*;

/**
 * Validates a workflow definition at publish time (see 03-API-Design.md §3.1).
 * Returns a list of human-readable issues; empty means valid.
 */
@Component
public class DefinitionValidator {

    private static final Set<String> KNOWN_TYPES =
            Set.of("http_request", "condition", "delay", "notify", "ai", "approval");

    public List<String> validate(WorkflowDefinition def) {
        List<String> issues = new ArrayList<>();
        if (def == null) {
            issues.add("definition is null or unparseable");
            return issues;
        }
        if (def.nodes == null || def.nodes.isEmpty()) {
            issues.add("definition has no nodes");
            return issues;
        }
        if (def.start == null || def.start.isBlank()) {
            issues.add("definition has no 'start' node");
        } else if (!def.nodes.containsKey(def.start)) {
            issues.add("'start' points to unknown node '" + def.start + "'");
        }

        for (Map.Entry<String, NodeDef> e : def.nodes.entrySet()) {
            String id = e.getKey();
            NodeDef n = e.getValue();
            if (n == null) { issues.add("node '" + id + "' is null"); continue; }
            if (n.type == null || !KNOWN_TYPES.contains(n.type)) {
                issues.add("node '" + id + "' has unknown type '" + n.type + "'");
            }
            if (n.isBranching()) {
                checkTarget(def, issues, id, "onTrue", n.onTrue, true);
                checkTarget(def, issues, id, "onFalse", n.onFalse, true);
            } else {
                // next may be null (terminal) but if present must resolve
                checkTarget(def, issues, id, "next", n.next, false);
            }
        }

        // Reachability from start
        if (def.start != null && def.nodes.containsKey(def.start)) {
            Set<String> reachable = reachableFrom(def);
            for (String id : def.nodes.keySet()) {
                if (!reachable.contains(id)) {
                    issues.add("node '" + id + "' is unreachable from start");
                }
            }
        }
        return issues;
    }

    private void checkTarget(WorkflowDefinition def, List<String> issues,
                             String nodeId, String field, String target, boolean required) {
        if (target == null || target.isBlank()) {
            if (required) {
                issues.add("node '" + nodeId + "' is missing required '" + field + "'");
            }
            return;
        }
        if (!def.nodes.containsKey(target)) {
            issues.add("node '" + nodeId + "' has '" + field + "' pointing to unknown node '" + target + "'");
        }
    }

    private Set<String> reachableFrom(WorkflowDefinition def) {
        Set<String> seen = new HashSet<>();
        Deque<String> stack = new ArrayDeque<>();
        stack.push(def.start);
        while (!stack.isEmpty()) {
            String id = stack.pop();
            if (id == null || !seen.add(id)) continue;
            NodeDef n = def.nodes.get(id);
            if (n == null) continue;
            for (String t : new String[]{n.next, n.onTrue, n.onFalse}) {
                if (t != null && !seen.contains(t)) stack.push(t);
            }
        }
        return seen;
    }
}
