package com.relay.ai;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class MockLlmProviderTest {

    private final MockLlmProvider provider = new MockLlmProvider();

    @Test
    void returnMarkerDrivesExactOutput() {
        LlmResponse r = provider.complete(new LlmRequest("classify this. return:{\"decision\":\"charge\"}"));
        assertThat(r.content()).isEqualTo("{\"decision\":\"charge\"}");
        assertThat(r.completionTokens()).isGreaterThan(0);
    }

    @Test
    void withoutMarkerEchoesJson() {
        LlmResponse r = provider.complete(new LlmRequest("hello world"));
        assertThat(r.content()).contains("echo");
        assertThat(r.promptTokens()).isGreaterThan(0);
    }
}
