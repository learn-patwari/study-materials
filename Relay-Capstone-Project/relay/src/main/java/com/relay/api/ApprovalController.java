package com.relay.api;

import com.relay.domain.Approval;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/approvals")
public class ApprovalController {

    private final ApprovalService service;

    public ApprovalController(ApprovalService service) {
        this.service = service;
    }

    @GetMapping
    public List<Dtos.ApprovalView> list(@RequestParam(defaultValue = "PENDING") String status) {
        // v1 exposes the pending inbox; status param reserved for future filters.
        return service.listPending().stream().map(this::toView).toList();
    }

    @PostMapping("/{id}/grant")
    public Dtos.ApprovalView grant(@PathVariable UUID id,
                                   @RequestBody(required = false) Dtos.DecisionRequest req) {
        return toView(service.grant(id, req == null ? null : req.decidedBy()));
    }

    @PostMapping("/{id}/reject")
    public Dtos.ApprovalView reject(@PathVariable UUID id,
                                    @RequestBody(required = false) Dtos.DecisionRequest req) {
        return toView(service.reject(id, req == null ? null : req.decidedBy()));
    }

    private Dtos.ApprovalView toView(Approval a) {
        return new Dtos.ApprovalView(a.getId(), a.getRunId(), a.getNodeId(),
                a.getStatus().name(), a.getDecidedBy(), a.getCreatedAt());
    }
}
