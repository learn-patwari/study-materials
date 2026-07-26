package com.relay.api;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.relay.domain.Workflow;
import com.relay.domain.WorkflowVersion;
import com.relay.domain.VersionStatus;
import com.relay.engine.DefinitionValidator;
import com.relay.engine.model.WorkflowDefinition;
import com.relay.persistence.WorkflowRepository;
import com.relay.persistence.WorkflowVersionRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.security.SecureRandom;
import java.util.HexFormat;
import java.util.List;
import java.util.UUID;

@Service
public class WorkflowService {

    private final WorkflowRepository workflows;
    private final WorkflowVersionRepository versions;
    private final DefinitionValidator validator;
    private final ObjectMapper mapper;
    private final SecureRandom random = new SecureRandom();

    public WorkflowService(WorkflowRepository workflows, WorkflowVersionRepository versions,
                           DefinitionValidator validator, ObjectMapper mapper) {
        this.workflows = workflows;
        this.versions = versions;
        this.validator = validator;
        this.mapper = mapper;
    }

    @Transactional
    public Workflow create(String name) {
        Workflow w = new Workflow();
        w.setName(name);
        byte[] secret = new byte[32];
        random.nextBytes(secret);
        w.setSecret(HexFormat.of().formatHex(secret));
        return workflows.save(w);
    }

    public Workflow get(UUID id) {
        return workflows.findById(id)
                .orElseThrow(() -> new ApiExceptions.NotFoundException("workflow " + id + " not found"));
    }

    public List<WorkflowVersion> versions(UUID workflowId) {
        get(workflowId);
        return versions.findByWorkflowIdOrderByVersionDesc(workflowId);
    }

    /** Create or update the latest draft version with a new definition. */
    @Transactional
    public WorkflowVersion upsertDraft(UUID workflowId, String definitionJson) {
        get(workflowId);
        parseOrThrow(definitionJson); // must be valid JSON (structure checked at publish)

        List<WorkflowVersion> existing = versions.findByWorkflowIdOrderByVersionDesc(workflowId);
        WorkflowVersion target;
        if (!existing.isEmpty() && existing.get(0).getStatus() == VersionStatus.DRAFT) {
            target = existing.get(0);
            target.setDefinition(definitionJson);
        } else {
            int next = existing.isEmpty() ? 1 : existing.get(0).getVersion() + 1;
            target = new WorkflowVersion();
            target.setWorkflowId(workflowId);
            target.setVersion(next);
            target.setStatus(VersionStatus.DRAFT);
            target.setDefinition(definitionJson);
        }
        return versions.save(target);
    }

    /** Publish freezes an immutable, runnable snapshot after validation. */
    @Transactional
    public WorkflowVersion publish(UUID workflowId, int version) {
        Workflow w = get(workflowId);
        WorkflowVersion v = versions.findByWorkflowIdAndVersion(workflowId, version)
                .orElseThrow(() -> new ApiExceptions.NotFoundException(
                        "version " + version + " not found for workflow " + workflowId));

        WorkflowDefinition def = parseOrThrow(v.getDefinition());
        List<String> issues = validator.validate(def);
        if (!issues.isEmpty()) {
            throw new ApiExceptions.ValidationException("definition is not publishable", issues);
        }
        v.setStatus(VersionStatus.PUBLISHED);
        versions.save(v);
        w.setPublishedVersionId(v.getId());
        workflows.save(w);
        return v;
    }

    private WorkflowDefinition parseOrThrow(String json) {
        try {
            JsonNode tree = mapper.readTree(json);
            return mapper.treeToValue(tree, WorkflowDefinition.class);
        } catch (Exception e) {
            throw new ApiExceptions.ValidationException("definition is not valid JSON",
                    List.of(e.getMessage()));
        }
    }
}
