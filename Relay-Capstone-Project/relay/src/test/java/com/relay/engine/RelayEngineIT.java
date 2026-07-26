package com.relay.engine;

import com.relay.api.TriggerService;
import com.relay.api.WorkflowService;
import com.relay.domain.Run;
import com.relay.domain.RunStatus;
import com.relay.external.MockExternalWorld;
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
    @Autowired OutboxProcessor processor;
    @Autowired RunRepository runs;
    @Autowired SideEffectRepository sideEffects;
    @Autowired MockExternalWorld world;

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
        var wf = workflows.create("orders");
        workflows.upsertDraft(wf.getId(), DEFINITION);
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
}
