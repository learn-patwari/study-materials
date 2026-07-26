package com.relay.ai;

import org.springframework.stereotype.Component;

/**
 * Deterministic mock LLM. If the prompt contains {@code return:<json>}, everything after the
 * marker is returned verbatim as the content — so tests/workflows can drive exact AI output.
 * Otherwise it echoes a small JSON object. Token counts are derived deterministically.
 */
@Component
public class MockLlmProvider implements LlmProvider {

    private static final String MARKER = "return:";

    @Override
    public LlmResponse complete(LlmRequest request) {
        String prompt = request.prompt() == null ? "" : request.prompt();
        String content;
        int idx = prompt.indexOf(MARKER);
        if (idx >= 0) {
            content = prompt.substring(idx + MARKER.length()).trim();
        } else {
            String echo = prompt.length() > 60 ? prompt.substring(0, 60) : prompt;
            content = "{\"echo\":\"" + echo.replace("\"", "'") + "\"}";
        }
        int promptTokens = Math.max(1, prompt.length() / 4);
        int completionTokens = Math.max(1, content.length() / 4);
        return new LlmResponse(content, promptTokens, completionTokens);
    }
}
