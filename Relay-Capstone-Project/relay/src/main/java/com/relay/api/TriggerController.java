package com.relay.api;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;

@RestController
@RequestMapping("/api/triggers")
public class TriggerController {

    private final TriggerService service;

    public TriggerController(TriggerService service) {
        this.service = service;
    }

    @PostMapping("/{workflowId}/manual")
    @ResponseStatus(HttpStatus.ACCEPTED)
    public Dtos.TriggerResult manual(@PathVariable UUID workflowId,
                                     @RequestBody(required = false) String payload) {
        UUID runId = service.triggerManual(workflowId, payload);
        return new Dtos.TriggerResult(runId, "PENDING");
    }

    @PostMapping("/{workflowId}/webhook")
    @ResponseStatus(HttpStatus.ACCEPTED)
    public Dtos.TriggerResult webhook(@PathVariable UUID workflowId,
                                      @RequestBody String rawBody,
                                      @RequestHeader(value = "X-Relay-Signature", required = false) String signature) {
        UUID runId = service.triggerWebhook(workflowId, rawBody, signature);
        return new Dtos.TriggerResult(runId, "PENDING");
    }
}
