package com.relay.engine;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.relay.engine.model.WorkflowDefinition;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class DefinitionValidatorTest {

    private final ObjectMapper mapper = new ObjectMapper();
    private final DefinitionValidator validator = new DefinitionValidator();

    private WorkflowDefinition parse(String json) throws Exception {
        return mapper.readValue(json, WorkflowDefinition.class);
    }

    @Test
    void validLinearWorkflowHasNoIssues() throws Exception {
        var def = parse("""
            { "start": "a",
              "nodes": {
                "a": { "type": "notify", "next": "b", "config": { "template": "hi" } },
                "b": { "type": "notify", "next": null,  "config": { "template": "bye" } }
              } }
            """);
        assertThat(validator.validate(def)).isEmpty();
    }

    @Test
    void danglingNextIsReported() throws Exception {
        var def = parse("""
            { "start": "a",
              "nodes": { "a": { "type": "notify", "next": "ghost" } } }
            """);
        List<String> issues = validator.validate(def);
        assertThat(issues).anyMatch(s -> s.contains("unknown node 'ghost'"));
    }

    @Test
    void missingStartIsReported() throws Exception {
        var def = parse("""
            { "nodes": { "a": { "type": "notify" } } }
            """);
        assertThat(validator.validate(def)).anyMatch(s -> s.contains("no 'start'"));
    }

    @Test
    void unreachableNodeIsReported() throws Exception {
        var def = parse("""
            { "start": "a",
              "nodes": {
                "a": { "type": "notify", "next": null },
                "orphan": { "type": "notify", "next": null }
              } }
            """);
        assertThat(validator.validate(def)).anyMatch(s -> s.contains("unreachable"));
    }

    @Test
    void conditionMissingBranchIsReported() throws Exception {
        var def = parse("""
            { "start": "c",
              "nodes": {
                "c": { "type": "condition", "config": { "expr": "1 > 0" }, "onTrue": "x" },
                "x": { "type": "notify", "next": null }
              } }
            """);
        assertThat(validator.validate(def)).anyMatch(s -> s.contains("missing required 'onFalse'"));
    }

    @Test
    void unknownTypeIsReported() throws Exception {
        var def = parse("""
            { "start": "a", "nodes": { "a": { "type": "teleport", "next": null } } }
            """);
        assertThat(validator.validate(def)).anyMatch(s -> s.contains("unknown type 'teleport'"));
    }
}
