package com.relay.engine;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class TemplateResolverTest {

    private final ObjectMapper mapper = new ObjectMapper();
    private final TemplateResolver resolver = new TemplateResolver();

    private JsonNode scope() throws Exception {
        return mapper.readTree("""
            { "input": { "orderId": "A-1001", "amount": 2499 },
              "fetch_order": { "id": "A-1001", "amount": 2499 } }
            """);
    }

    @Test
    void resolvesNestedPaths() throws Exception {
        assertThat(resolver.resolve("Order {{input.orderId}} amount {{fetch_order.amount}}", scope()))
                .isEqualTo("Order A-1001 amount 2499");
    }

    @Test
    void leavesPlainStringUnchanged() throws Exception {
        assertThat(resolver.resolve("no templates here", scope())).isEqualTo("no templates here");
    }

    @Test
    void missingPathThrows() throws Exception {
        assertThatThrownBy(() -> resolver.resolve("{{input.missing}}", scope()))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("input.missing");
    }
}
