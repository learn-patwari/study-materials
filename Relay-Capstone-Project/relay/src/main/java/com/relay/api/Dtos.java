package com.relay.api;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.validation.constraints.NotBlank;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

/** Request/response DTOs for the REST API. */
public final class Dtos {

    private Dtos() {}

    public record CreateWorkflowRequest(@NotBlank String name) {}

    public record WorkflowCreated(UUID id, String name, String secret) {}

    public record VersionView(UUID id, int version, String status) {}

    public record WorkflowView(UUID id, String name, UUID publishedVersionId, List<VersionView> versions) {}

    public record PublishResult(UUID versionId, int version, String status) {}

    public record TriggerResult(UUID runId, String status) {}

    public record RunSummary(UUID id, String status, String currentNode, int stepCount, OffsetDateTime createdAt) {}

    public record StepView(String nodeId, int attempt, String status, JsonNode input, JsonNode output,
                           String error, OffsetDateTime startedAt, OffsetDateTime finishedAt) {}

    public record RunDetail(UUID id, String status, String currentNode, int stepCount,
                            JsonNode input, List<StepView> steps) {}

    public record TraceView(String nodeId, String kind, JsonNode detail, OffsetDateTime createdAt) {}

    public record ApprovalView(UUID id, UUID runId, String nodeId, String status,
                               String decidedBy, OffsetDateTime createdAt) {}

    public record DecisionRequest(String decidedBy) {}
}
