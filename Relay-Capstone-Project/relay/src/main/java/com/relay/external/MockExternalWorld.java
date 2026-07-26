package com.relay.external;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * The mocked external world. Every effect is keyed by an idempotency key and performed
 * at most once — a second call with the same key REPLAYS the stored result without
 * re-performing. This is what makes side effects exactly-once even across worker crashes
 * (see 10-Hard-Problems.md §10.1). "Flaky" mode injects a one-time transient failure per
 * key BEFORE any effect is recorded, to exercise retries.
 */
@Component
public class MockExternalWorld {

    private final ObjectMapper mapper;
    private final boolean flaky;

    /** key -> recorded effect result (proves at-most-once). */
    private final Map<String, JsonNode> performed = new ConcurrentHashMap<>();
    /** keys that have already been failed once (flaky mode). */
    private final Set<String> failedOnce = ConcurrentHashMap.newKeySet();

    public MockExternalWorld(ObjectMapper mapper,
                             @Value("${relay.http-adapter.flaky:false}") boolean flaky) {
        this.mapper = mapper;
        this.flaky = flaky;
    }

    public JsonNode http(String key, String method, String url, JsonNode body) {
        JsonNode existing = performed.get(key);
        if (existing != null) return existing;              // replay, no duplicate effect
        maybeFail(key);
        ObjectNode result = mapper.createObjectNode();
        result.put("status", 200);
        result.put("method", method == null ? "GET" : method);
        result.put("url", url);
        result.set("echo", body == null ? mapper.nullNode() : body);
        performed.put(key, result);
        return result;
    }

    public JsonNode notify(String key, String to, String message) {
        JsonNode existing = performed.get(key);
        if (existing != null) return existing;
        maybeFail(key);
        ObjectNode result = mapper.createObjectNode();
        result.put("notified", true);
        result.put("to", to);
        result.put("message", message);
        performed.put(key, result);
        return result;
    }

    private void maybeFail(String key) {
        if (flaky && failedOnce.add(key)) {
            throw new RuntimeException("transient failure (flaky) for key " + key);
        }
    }

    /** Test/demo helper: how many distinct effects were actually performed. */
    public int performedCount() { return performed.size(); }

    public boolean wasPerformed(String key) { return performed.containsKey(key); }

    /** Test helper: clear recorded effects between tests (the real world has no such button). */
    public void reset() {
        performed.clear();
        failedOnce.clear();
    }
}
