package com.relay.api;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.relay.domain.Approval;
import com.relay.domain.ApprovalStatus;
import com.relay.domain.OutboxMessage;
import com.relay.domain.Run;
import com.relay.domain.RunStatus;
import com.relay.engine.TraceService;
import com.relay.persistence.ApprovalRepository;
import com.relay.persistence.OutboxRepository;
import com.relay.persistence.RunRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

/**
 * Human approval decisions. Granting resumes the parked run by enqueuing an outbox message
 * in the SAME transaction as the decision; the engine re-checks the gate on resume, so the
 * decision is enforced structurally (see 04-Execution-Engine.md §4.5).
 */
@Service
public class ApprovalService {

    private final ApprovalRepository approvals;
    private final RunRepository runs;
    private final OutboxRepository outbox;
    private final TraceService traces;
    private final ObjectMapper mapper;

    public ApprovalService(ApprovalRepository approvals, RunRepository runs, OutboxRepository outbox,
                           TraceService traces, ObjectMapper mapper) {
        this.approvals = approvals;
        this.runs = runs;
        this.outbox = outbox;
        this.traces = traces;
        this.mapper = mapper;
    }

    public List<Approval> listPending() {
        return approvals.findByStatusOrderByCreatedAt(ApprovalStatus.PENDING);
    }

    @Transactional
    public Approval grant(UUID id, String decidedBy) {
        Approval a = decide(id, ApprovalStatus.GRANTED, decidedBy);
        Run run = runs.findByIdForUpdate(a.getRunId())
                .orElseThrow(() -> new ApiExceptions.NotFoundException("run not found"));
        run.setStatus(RunStatus.RUNNING);
        run.setUpdatedAt(OffsetDateTime.now());
        runs.save(run);

        OutboxMessage msg = new OutboxMessage();
        msg.setRunId(run.getId());
        msg.setAvailableAt(OffsetDateTime.now());
        msg.setStatus("READY");
        outbox.save(msg);

        traces.record(run.getId(), a.getNodeId(), "GATE",
                mapper.createObjectNode().put("status", "GRANTED").put("by", nullSafe(decidedBy)));
        return a;
    }

    @Transactional
    public Approval reject(UUID id, String decidedBy) {
        Approval a = decide(id, ApprovalStatus.REJECTED, decidedBy);
        Run run = runs.findByIdForUpdate(a.getRunId())
                .orElseThrow(() -> new ApiExceptions.NotFoundException("run not found"));
        run.setStatus(RunStatus.FAILED);
        run.setUpdatedAt(OffsetDateTime.now());
        runs.save(run);

        traces.record(run.getId(), a.getNodeId(), "GATE",
                mapper.createObjectNode().put("status", "REJECTED").put("by", nullSafe(decidedBy)));
        return a;
    }

    private Approval decide(UUID id, ApprovalStatus decision, String decidedBy) {
        Approval a = approvals.findById(id)
                .orElseThrow(() -> new ApiExceptions.NotFoundException("approval " + id + " not found"));
        if (a.getStatus() != ApprovalStatus.PENDING) {
            throw new ApiExceptions.BadRequestException("approval already decided: " + a.getStatus());
        }
        a.setStatus(decision);
        a.setDecidedBy(decidedBy);
        a.setDecidedAt(OffsetDateTime.now());
        return approvals.save(a);
    }

    private String nullSafe(String s) { return s == null ? "unknown" : s; }
}
