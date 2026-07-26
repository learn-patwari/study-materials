package com.relay.api;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.relay.domain.Run;
import com.relay.domain.Step;
import com.relay.domain.Trace;
import com.relay.persistence.RunRepository;
import com.relay.persistence.StepRepository;
import com.relay.persistence.TraceRepository;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/runs")
public class RunController {

    private final RunRepository runs;
    private final StepRepository steps;
    private final TraceRepository traces;
    private final ObjectMapper mapper;

    public RunController(RunRepository runs, StepRepository steps, TraceRepository traces, ObjectMapper mapper) {
        this.runs = runs;
        this.steps = steps;
        this.traces = traces;
        this.mapper = mapper;
    }

    @GetMapping
    public List<Dtos.RunSummary> list() {
        return runs.findTop100ByOrderByCreatedAtDesc().stream().map(this::summary).toList();
    }

    @GetMapping("/{id}")
    public Dtos.RunDetail get(@PathVariable UUID id) {
        Run r = find(id);
        List<Dtos.StepView> stepViews = steps.findByRunIdOrderByStartedAt(id).stream()
                .map(this::stepView).toList();
        return new Dtos.RunDetail(r.getId(), r.getStatus().name(), r.getCurrentNode(),
                r.getStepCount(), read(r.getInput()), stepViews);
    }

    @GetMapping("/{id}/trace")
    public List<Dtos.TraceView> trace(@PathVariable UUID id) {
        find(id);
        return traces.findByRunIdOrderByCreatedAt(id).stream()
                .map(t -> new Dtos.TraceView(t.getNodeId(), t.getKind(), read(t.getDetail()), t.getCreatedAt()))
                .toList();
    }

    private Run find(UUID id) {
        return runs.findById(id)
                .orElseThrow(() -> new ApiExceptions.NotFoundException("run " + id + " not found"));
    }

    private Dtos.RunSummary summary(Run r) {
        return new Dtos.RunSummary(r.getId(), r.getStatus().name(), r.getCurrentNode(),
                r.getStepCount(), r.getCreatedAt());
    }

    private Dtos.StepView stepView(Step s) {
        return new Dtos.StepView(s.getNodeId(), s.getAttempt(), s.getStatus().name(),
                read(s.getInput()), read(s.getOutput()), s.getError(), s.getStartedAt(), s.getFinishedAt());
    }

    private JsonNode read(String json) {
        try { return json == null ? null : mapper.readTree(json); }
        catch (Exception e) { return null; }
    }
}
