package com.relay.ai;

/** A request to an LLM provider. Kept minimal and provider-agnostic. */
public record LlmRequest(String prompt) {
}
