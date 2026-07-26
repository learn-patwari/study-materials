package com.relay.engine;

import com.relay.api.TriggerService;
import com.relay.api.WorkflowService;
import com.relay.domain.RunStatus;
import com.relay.external.MockExternalWorld;
import com.relay.persistence.RunRepository;
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
 * Verifies retry/backoff (Phase 8): the mocked world's "flaky" mode fails the first call per
 * key; the engine retries and the run still succeeds with exactly-once effects.
 * Requires Docker. retry-base-ms=0 makes retries immediately claimable for a deterministic test.
 */
@SpringBootTest
@Testcontainers
@TestPropertySource(properties = {
        "relay.engine.enabled=false",
        "relay.http-adapter.flaky=true",
        "relay.engine.retry-base-ms=0"
})
class RetryIT {

    @Container
    @ServiceConnection
    static PostgreSQLContainer<?> POSTGRES = new PostgreSQLContainer<>("postgres:16-alpine");

    @Autowired WorkflowService workflows;
    @Autowired TriggerService triggers;
    @Autowired OutboxProcessor processor;
    @Autowired RunRepository runs;
    @Autowired MockExternalWorld world;

    private static final String DEF = """
        { "start": "charge",
          "nodes": {
            "charge": { "type": "http_request", "next": "done",
                        "config": { "method": "POST", "url": "https://api.mock/orders" } },
            "done":   { "type": "notify", "next": null, "config": { "to": "ops", "template": "ok" } }
          } }
        """;

    @Test
    void transientFailureIsRetriedAndRunSucceedsExactlyOnce() {
        var wf = workflows.create("retry");
        workflows.upsertDraft(wf.getId(), DEF);
        workflows.publish(wf.getId(), 1);
        UUID runId = triggers.triggerManual(wf.getId(), "{}");

        int guard = 0;
        while (processor.claimAndAdvanceOne() && guard++ < 1000) { /* drain incl. retries */ }

        assertThat(runs.findById(runId).orElseThrow().getStatus()).isEqualTo(RunStatus.SUCCEEDED);
        // charge + notify each performed exactly once despite a transient failure on each
        assertThat(world.performedCount()).isEqualTo(2);
    }
}
