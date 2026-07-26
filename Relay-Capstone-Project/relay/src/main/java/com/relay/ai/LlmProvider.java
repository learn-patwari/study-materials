package com.relay.ai;

/**
 * Provider adapter for an LLM. Mocked for the capstone and pluggable
 * (LangChain/LangGraph-compatible shape) so a real provider drops in later.
 */
public interface LlmProvider {
    LlmResponse complete(LlmRequest request);
}
