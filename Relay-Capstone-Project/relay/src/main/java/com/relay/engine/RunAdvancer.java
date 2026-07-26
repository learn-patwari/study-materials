package com.relay.engine;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.fasterxml.jackson.databind.node.TextNode;
import com.relay.domain.*;
import com.relay.engine.model.NodeDef;
import com.relay.engine.model.WorkflowDefinition;
import com.relay.nodes.NodeContext;
import com.relay.nodes.NodeExecutorRegistry;
import com.relay.nodes.NodeResult;
import com.relay.persistence.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.OffsetDateTime;
import java.util.EnumSet;
import java.util.Set;
import java.util.UUID;

/**
 * Advances a run by exactly ONE node, persisting the step, cursor, and trace in the
 * caller's transaction, and enqueuing the next message if the run should continue.
 * One node per message = per-node atomicity, so a crash resumes from the same node
 * (idempotency makes the side effect exactly-once). See 04-Execution-Engine.md.
 */
@Service
public class RunAdvancer {

    private static final Set<RunStatus> TERMINAL =
            EnumSet.of(RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED);

    private final RunRepository runRepo;
    private final WorkflowVersionRepository versionRepo;
    private final StepRepository stepRepo;
    private final OutboxRepository outboxRepo;
    private final ApprovalRepository approvalRepo;
    private final NodeExecutorRegistry registry;
    private final TemplateResolver templates;
    private final TraceService traces;
    private final ObjectMapper mapper;
    private final int maxSteps;

    public RunAdvancer(RunRepository runRepo, WorkflowVersionRepository versionRepo,
                       StepRepository stepRepo, OutboxRepository outboxRepo,
                       ApprovalRepository approvalRepo,
                       NodeExecutorRegistry registry, TemplateResolver templates,
                       TraceService traces, ObjectMapper mapper,
                       @Value("${relay.guardrails.max-steps:100}") int maxSteps) {
        this.runRepo = runRepo;
        this.versionRepo = versionRepo;
        this.stepRepo = stepRepo;
        this.outboxRepo = outboxRepo;
        this.approvalRepo = approvalRepo;
        this.registry = registry;
        this.templates = templates;
        this.traces = traces;
        this.mapper = mapper;
        this.maxSteps = maxSteps;
    }

    /** Runs within the caller's transaction (OutboxProcessor). */
    public void advanceOneNode(UUID runId) {
        Run run = runRepo.findByIdForUpdate(runId).orElse(null);
        if (run == null || TERMINAL.contains(run.getStatus())
                || run.getStatus() == RunStatus.WAITING_APPROVAL) {
            return; // nothing to do (idempotent)
        }

        WorkflowVersion ver = versionRepo.findById(run.getVersionId()).orElseThrow();
        WorkflowDefinition def = parse(ver.getDefinition());

        String nodeId = run.getCurrentNode() != null ? run.getCurrentNode() : def.start;
        if (nodeId == null) { finish(run, RunStatus.SUCCEEDED); return; }

        // Guardrail: hard step cap (a guardrail you can't turn off)
        if (run.getStepCount() >= maxSteps) {
            traces.record(runId, nodeId, "GUARDRAIL", detail("reason", "max_steps_exceeded"));
            finish(run, RunStatus.FAILED);
            return;
        }

        NodeDef node = def.node(nodeId);
        if (node == null) { failRun(run, nodeId, "unknown node '" + nodeId + "'"); return; }

        // Approval gate: sensitive nodes (and explicit approval nodes) are hard-blocked in the
        // ENGINE until a GRANTED approval exists — never delegated to the AI (see 06/10 docs).
        boolean isGate = "approval".equals(node.type) || node.sensitive;
        if (isGate && approvalRepo.findByRunIdAndNodeIdAndStatus(runId, nodeId, ApprovalStatus.GRANTED).isEmpty()) {
            park(run, nodeId);
            return;
        }

        JsonNode scope = buildScope(run);
        JsonNode resolvedConfig = resolve(node.config, scope);

        int attempt = stepRepo.countByRunIdAndNodeId(runId, nodeId) + 1;
        Step step = new Step();
        step.setRunId(runId);
        step.setNodeId(nodeId);
        step.setAttempt(attempt);
        step.setStatus(StepStatus.RUNNING);
        step.setInput(write(resolvedConfig));
        step = stepRepo.save(step);
        traces.record(runId, nodeId, "INPUT_RESOLVED", resolvedConfig);

        try {
            NodeResult result;
            if ("approval".equals(node.type)) {
                // Gate already granted (checked above); pass through.
                result = NodeResult.of(mapper.createObjectNode().put("approved", true));
            } else {
                NodeContext ctx = new NodeContext(runId, nodeId, resolvedConfig, mapper);
                result = registry.get(node.type).execute(ctx);
            }

            step.setStatus(StepStatus.SUCCEEDED);
            step.setOutput(write(result.output()));
            step.setFinishedAt(OffsetDateTime.now());
            stepRepo.save(step);
            traces.record(runId, nodeId, "NODE_RESULT", result.output());

            String next = node.isBranching()
                    ? (Boolean.TRUE.equals(result.branchResult()) ? node.onTrue : node.onFalse)
                    : node.next;

            run.setStepCount(run.getStepCount() + 1);
            run.setCurrentNode(next);
            run.setUpdatedAt(OffsetDateTime.now());

            if (next == null) {
                run.setStatus(RunStatus.SUCCEEDED);
                traces.record(runId, null, "RUN_FINISHED", detail("status", "SUCCEEDED"));
            } else {
                run.setStatus(RunStatus.RUNNING);
                long delayMs = "delay".equals(node.type) ? resolvedConfig.path("durationMs").asLong(0) : 0;
                enqueue(runId, OffsetDateTime.now().plusNanos(delayMs * 1_000_000));
            }
            runRepo.save(run);
        } catch (Exception ex) {
            // v1: node error fails the run (retry/backoff is Phase 8).
            step.setStatus(StepStatus.FAILED);
            step.setError(ex.getMessage());
            step.setFinishedAt(OffsetDateTime.now());
            stepRepo.save(step);
            traces.record(runId, nodeId, "NODE_ERROR", detail("error", String.valueOf(ex.getMessage())));
            failRun(run, nodeId, ex.getMessage());
        }
    }

    // --- helpers ---------------------------------------------------------

    private JsonNode buildScope(Run run) {
        ObjectNode scope = mapper.createObjectNode();
        scope.set("input", read(run.getInput()));
        for (Step s : stepRepo.findByRunIdOrderByStartedAt(run.getId())) {
            if (s.getStatus() == StepStatus.SUCCEEDED && s.getOutput() != null) {
                scope.set(s.getNodeId(), read(s.getOutput()));
            }
        }
        return scope;
    }

    private JsonNode resolve(JsonNode node, JsonNode scope) {
        if (node == null || node.isNull() || node.isMissingNode()) return mapper.nullNode();
        if (node.isTextual()) return TextNode.valueOf(templates.resolve(node.asText(), scope));
        if (node.isObject()) {
            ObjectNode out = mapper.createObjectNode();
            node.fields().forEachRemaining(e -> out.set(e.getKey(), resolve(e.getValue(), scope)));
            return out;
        }
        if (node.isArray()) {
            ArrayNode out = mapper.createArrayNode();
            node.forEach(el -> out.add(resolve(el, scope)));
            return out;
        }
        return node;
    }

    private void enqueue(UUID runId, OffsetDateTime availableAt) {
        OutboxMessage msg = new OutboxMessage();
        msg.setRunId(runId);
        msg.setAvailableAt(availableAt);
        msg.setStatus("READY");
        outboxRepo.save(msg);
    }

    /** Park a run at a gate: create a PENDING approval (idempotent) and wait — do NOT enqueue. */
    private void park(Run run, String nodeId) {
        if (approvalRepo.findByRunIdAndNodeId(run.getId(), nodeId).isEmpty()) {
            Approval a = new Approval();
            a.setRunId(run.getId());
            a.setNodeId(nodeId);
            a.setStatus(ApprovalStatus.PENDING);
            approvalRepo.save(a);
        }
        run.setStatus(RunStatus.WAITING_APPROVAL);
        run.setCurrentNode(nodeId);
        run.setUpdatedAt(OffsetDateTime.now());
        runRepo.save(run);
        traces.record(run.getId(), nodeId, "GATE", detail("status", "WAITING_APPROVAL"));
    }

    private void finish(Run run, RunStatus status) {
        run.setStatus(status);
        run.setUpdatedAt(OffsetDateTime.now());
        runRepo.save(run);
        traces.record(run.getId(), null, "RUN_FINISHED", detail("status", status.name()));
    }

    private void failRun(Run run, String nodeId, String error) {
        run.setStatus(RunStatus.FAILED);
        run.setUpdatedAt(OffsetDateTime.now());
        runRepo.save(run);
        traces.record(run.getId(), nodeId, "RUN_FINISHED", detail("status", "FAILED"));
    }

    private WorkflowDefinition parse(String json) {
        try {
            return mapper.readValue(json, WorkflowDefinition.class);
        } catch (Exception e) {
            throw new IllegalStateException("unparseable definition", e);
        }
    }

    private JsonNode read(String json) {
        try { return json == null ? mapper.nullNode() : mapper.readTree(json); }
        catch (Exception e) { return mapper.nullNode(); }
    }

    private String write(JsonNode node) {
        try { return mapper.writeValueAsString(node == null ? mapper.nullNode() : node); }
        catch (Exception e) { return "null"; }
    }

    private ObjectNode detail(String k, String v) {
        return mapper.createObjectNode().put(k, v);
    }
}
