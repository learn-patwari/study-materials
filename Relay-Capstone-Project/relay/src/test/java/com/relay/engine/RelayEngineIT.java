package com.relay.engine;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.relay.api.ApprovalService;
import com.relay.api.TriggerService;
import com.relay.api.WorkflowService;
import com.relay.domain.Approval;
import com.relay.domain.ApprovalStatus;
import com.relay.domain.Run;
import com.relay.domain.RunStatus;
import com.relay.external.MockExternalWorld;
import com.relay.persistence.ApprovalRepository;
import com.relay.persistence.RunRepository;
import com.relay.persistence.SideEffectRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.test.context.TestPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Full-engine integration test. Requires Docker (Testcontainers Postgres); the scheduled
 * worker is disabled so the test drives the engine deterministically via OutboxProcessor.
 */
@SpringBootTest
@Testcontainers
@TestPropertySource(properties = "relay.engine.enabled=false")
class RelayEngineIT {

    @Container
    @ServiceConnection
    static PostgreSQLContainer<?> POSTGRES = new PostgreSQLContainer<>("postgres:16-alpine");

    @Autowired WorkflowService workflows;
    @Autowired TriggerService triggers;
    @Autowired ApprovalService approvalService;
    @Autowired OutboxProcessor processor;
    @Autowired RunRepository runs;
    @Autowired SideEffectRepository sideEffects;
    @Autowired ApprovalRepository approvals;
    @Autowired MockExternalWorld world;
    @Autowired ObjectMapper mapper;

    @BeforeEach
    void resetWorld() {
        world.reset();
    }

    private static final String DEFINITION = """
        { "start": "check",
          "nodes": {
            "check":       { "type": "condition", "config": { "expr": "{{input.amount}} > 1000" },
                             "onTrue": "charge", "onFalse": "notify_small" },
            "charge":      { "type": "http_request", "sensitive": true, "next": "notify_big",
                             "config": { "method": "POST", "url": "https://api.mock/orders",
                                         "body": { "amount": "{{input.amount}}" } } },
            "notify_big":  { "type": "notify", "next": null, "config": { "to": "ops", "template": "charged {{input.amount}}" } },
            "notify_small":{ "type": "notify", "next": null, "config": { "to": "ops", "template": "too small" } }
          } }
        """;

    private UUID publishAndTrigger(String payload) {
        return publishAndTrigger(DEFINITION, payload);
    }

    private UUID publishAndTrigger(String definition, String payload) {
        var wf = workflows.create("wf");
        workflows.upsertDraft(wf.getId(), definition);
        workflows.publish(wf.getId(), 1);
        return triggers.triggerManual(wf.getId(), payload);
    }

    private void drainQueue() {
        int guard = 0;
        while (processor.claimAndAdvanceOne() && guard++ < 100) {
            // keep draining
        }
    }

    @Test
    void runExecutesToSuccessWithExactlyOnceSideEffects() {
        UUID runId = publishAndTrigger("{\"amount\": 2499}");
        drainQueue();

        Run run = runs.findById(runId).orElseThrow();
        assertThat(run.getStatus()).isEqualTo(RunStatus.SUCCEEDED);
        // true branch: charge (http) + notify_big  => two distinct side effects, once each
        assertThat(world.performedCount()).isEqualTo(2);
        assertThat(sideEffects.findByRunIdAndNodeIdAndAttemptKey(runId, "charge", "call")).isPresent();
    }

    @Test
    void falseBranchSkipsTheChargeSideEffect() {
        UUID runId = publishAndTrigger("{\"amount\": 10}");
        drainQueue();

        Run run = runs.findById(runId).orElseThrow();
        assertThat(run.getStatus()).isEqualTo(RunStatus.SUCCEEDED);
        // false branch: only notify_small performed; charge never fired
        assertThat(world.performedCount()).isEqualTo(1);
        assertThat(sideEffects.findByRunIdAndNodeIdAndAttemptKey(runId, "charge", "call")).isEmpty();
    }

    // --- Phase 6: AI node ------------------------------------------------

    private String aiDefinition(String decision) throws Exception {
        ObjectNode def = mapper.createObjectNode();
        def.put("start", "classify");
        ObjectNode nodes = def.putObject("nodes");
        ObjectNode classify = nodes.putObject("classify");
        classify.put("type", "ai");
        classify.put("next", "done");
        ObjectNode cfg = classify.putObject("config");
        cfg.put("prompt", "decide. return:{\"decision\":\"" + decision + "\"}");
        ObjectNode schema = cfg.putObject("outputSchema");
        schema.put("type", "object");
        schema.putArray("required").add("decision");
        schema.putObject("properties").putObject("decision")
                .put("type", "string");
        ObjectNode done = nodes.putObject("done");
        done.put("type", "notify");
        done.putNull("next");
        done.putObject("config").put("to", "ops").put("template", "done");
        return mapper.writeValueAsString(def);
    }

    @Test
    void aiNodeOutputPassesSchemaAndFlowsDownstream() throws Exception {
        UUID runId = publishAndTrigger(aiDefinition("charge"), "{}");
        drainQueue();
        assertThat(runs.findById(runId).orElseThrow().getStatus()).isEqualTo(RunStatus.SUCCEEDED);
    }

    @Test
    void aiNodeInvalidSchemaFailsTheRun() throws Exception {
        // schema requires object with 'decision' string; force the model to return a bad shape
        String def = aiDefinition("charge").replace(
                "\"decision\":\"charge\"", "\"wrong\":123");
        UUID runId = publishAndTrigger(def, "{}");
        drainQueue();
        assertThat(runs.findById(runId).orElseThrow().getStatus()).isEqualTo(RunStatus.FAILED);
    }

    // --- Phase 7: Approval gates -----------------------------------------

    private static final String SENSITIVE_DEF = """
        { "start": "charge",
          "nodes": {
            "charge": { "type": "http_request", "sensitive": true, "next": "done",
                        "config": { "method": "POST", "url": "https://api.mock/orders" } },
            "done":   { "type": "notify", "next": null, "config": { "to": "ops", "template": "charged" } }
          } }
        """;

    @Test
    void sensitiveNodeParksForApprovalThenResumesExactlyOnce() {
        UUID runId = publishAndTrigger(SENSITIVE_DEF, "{}");
        drainQueue();

        // Parked: waiting on approval, charge NOT performed
        assertThat(runs.findById(runId).orElseThrow().getStatus()).isEqualTo(RunStatus.WAITING_APPROVAL);
        assertThat(world.performedCount()).isZero();
        Approval pending = approvals.findByRunIdAndNodeId(runId, "charge").orElseThrow();
        assertThat(pending.getStatus()).isEqualTo(ApprovalStatus.PENDING);

        // Grant → resume → charge fires exactly once
        approvalService.grant(pending.getId(), "alice");
        drainQueue();
        assertThat(runs.findById(runId).orElseThrow().getStatus()).isEqualTo(RunStatus.SUCCEEDED);
        assertThat(world.performedCount()).isEqualTo(1);
        assertThat(sideEffects.findByRunIdAndNodeIdAndAttemptKey(runId, "charge", "call")).isPresent();
    }

    @Test
    void rejectingApprovalFailsRunWithoutSideEffect() {
        UUID runId = publishAndTrigger(SENSITIVE_DEF, "{}");
        drainQueue();
        Approval pending = approvals.findByRunIdAndNodeId(runId, "charge").orElseThrow();

        approvalService.reject(pending.getId(), "bob");
        drainQueue();

        assertThat(runs.findById(runId).orElseThrow().getStatus()).isEqualTo(RunStatus.FAILED);
        assertThat(world.performedCount()).isZero();
    }
}
