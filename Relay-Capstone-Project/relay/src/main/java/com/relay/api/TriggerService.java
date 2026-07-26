package com.relay.api;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.relay.domain.OutboxMessage;
import com.relay.domain.Run;
import com.relay.domain.RunStatus;
import com.relay.domain.Workflow;
import com.relay.engine.TraceService;
import com.relay.persistence.OutboxRepository;
import com.relay.persistence.RunRepository;
import com.relay.persistence.WorkflowRepository;
import com.relay.security.HmacVerifier;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.UUID;

@Service
public class TriggerService {

    private final WorkflowRepository workflows;
    private final RunRepository runs;
    private final OutboxRepository outbox;
    private final TraceService traces;
    private final HmacVerifier hmac;
    private final ObjectMapper mapper;

    public TriggerService(WorkflowRepository workflows, RunRepository runs, OutboxRepository outbox,
                          TraceService traces, HmacVerifier hmac, ObjectMapper mapper) {
        this.workflows = workflows;
        this.runs = runs;
        this.outbox = outbox;
        this.traces = traces;
        this.hmac = hmac;
        this.mapper = mapper;
    }

    @Transactional
    public UUID triggerManual(UUID workflowId, String payloadJson) {
        Workflow w = workflows.findById(workflowId)
                .orElseThrow(() -> new ApiExceptions.NotFoundException("workflow " + workflowId + " not found"));
        return startRun(w, payloadJson);
    }

    @Transactional
    public UUID triggerWebhook(UUID workflowId, String rawBody, String signature) {
        Workflow w = workflows.findById(workflowId)
                .orElseThrow(() -> new ApiExceptions.NotFoundException("workflow " + workflowId + " not found"));
        if (!hmac.verify(w.getSecret(), rawBody, signature)) {
            throw new ApiExceptions.UnauthorizedException("invalid webhook signature");
        }
        return startRun(w, rawBody);
    }

    private UUID startRun(Workflow w, String payloadJson) {
        if (w.getPublishedVersionId() == null) {
            throw new ApiExceptions.BadRequestException("workflow has no published version");
        }
        String input = normalizeJson(payloadJson);

        Run run = new Run();
        run.setVersionId(w.getPublishedVersionId());
        run.setStatus(RunStatus.PENDING);
        run.setInput(input);
        run.setStepCount(0);
        run = runs.save(run);

        // Transactional outbox: enqueue in the SAME transaction as the run insert.
        OutboxMessage msg = new OutboxMessage();
        msg.setRunId(run.getId());
        msg.setAvailableAt(OffsetDateTime.now());
        msg.setStatus("READY");
        outbox.save(msg);

        traces.record(run.getId(), null, "RUN_STARTED", readOrEmpty(input));
        return run.getId();
    }

    private String normalizeJson(String payload) {
        try {
            return mapper.writeValueAsString(mapper.readTree(payload == null || payload.isBlank() ? "{}" : payload));
        } catch (Exception e) {
            throw new ApiExceptions.BadRequestException("trigger payload is not valid JSON");
        }
    }

    private com.fasterxml.jackson.databind.JsonNode readOrEmpty(String json) {
        try { return mapper.readTree(json); } catch (Exception e) { return mapper.createObjectNode(); }
    }
}
