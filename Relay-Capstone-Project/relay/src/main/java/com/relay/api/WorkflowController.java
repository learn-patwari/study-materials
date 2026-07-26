package com.relay.api;

import com.relay.domain.Workflow;
import com.relay.domain.WorkflowVersion;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/workflows")
public class WorkflowController {

    private final WorkflowService service;

    public WorkflowController(WorkflowService service) {
        this.service = service;
    }

    @PostMapping
    public Dtos.WorkflowCreated create(@Valid @RequestBody Dtos.CreateWorkflowRequest req) {
        Workflow w = service.create(req.name());
        return new Dtos.WorkflowCreated(w.getId(), w.getName(), w.getSecret());
    }

    @GetMapping("/{id}")
    public Dtos.WorkflowView get(@PathVariable UUID id) {
        Workflow w = service.get(id);
        List<Dtos.VersionView> vs = service.versions(id).stream()
                .map(this::toView).toList();
        return new Dtos.WorkflowView(w.getId(), w.getName(), w.getPublishedVersionId(), vs);
    }

    /** Body is the raw workflow definition JSON (see 02-Data-Model.md §2.4). */
    @PostMapping("/{id}/versions")
    public Dtos.VersionView upsertDraft(@PathVariable UUID id, @RequestBody String definitionJson) {
        return toView(service.upsertDraft(id, definitionJson));
    }

    @PostMapping("/{id}/versions/{version}/publish")
    public Dtos.PublishResult publish(@PathVariable UUID id, @PathVariable int version) {
        WorkflowVersion v = service.publish(id, version);
        return new Dtos.PublishResult(v.getId(), v.getVersion(), v.getStatus().name());
    }

    private Dtos.VersionView toView(WorkflowVersion v) {
        return new Dtos.VersionView(v.getId(), v.getVersion(), v.getStatus().name());
    }
}
