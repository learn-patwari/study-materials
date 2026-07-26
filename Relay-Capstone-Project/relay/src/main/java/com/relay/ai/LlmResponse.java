package com.relay.ai;

/** An LLM provider response: raw text (expected to be JSON) plus token usage. */
public record LlmResponse(String content, int promptTokens, int completionTokens) {
}
