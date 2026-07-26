package com.relay.ai;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class SchemaValidatorTest {

    private final ObjectMapper mapper = new ObjectMapper();
    private final SchemaValidator validator = new SchemaValidator();

    private JsonNode json(String s) throws Exception { return mapper.readTree(s); }

    private static final String SCHEMA = """
        { "type": "object",
          "required": ["decision"],
          "properties": { "decision": { "type": "string", "enum": ["charge", "skip"] } } }
        """;

    @Test
    void validOutputHasNoViolations() throws Exception {
        assertThat(validator.validate(json(SCHEMA), json("{\"decision\":\"charge\"}"))).isEmpty();
    }

    @Test
    void missingRequiredFieldIsViolation() throws Exception {
        assertThat(validator.validate(json(SCHEMA), json("{\"other\":1}"))).isNotEmpty();
    }

    @Test
    void wrongEnumValueIsViolation() throws Exception {
        assertThat(validator.validate(json(SCHEMA), json("{\"decision\":\"nuke\"}"))).isNotEmpty();
    }
}
