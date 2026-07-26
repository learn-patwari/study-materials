package com.relay.ai;

import com.fasterxml.jackson.databind.JsonNode;
import com.networknt.schema.JsonSchema;
import com.networknt.schema.JsonSchemaFactory;
import com.networknt.schema.SpecVersion;
import com.networknt.schema.ValidationMessage;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Set;

/**
 * Validates AI-node output against a JSON Schema. Only schema-valid output is allowed to
 * flow downstream (see 05-Node-Executors.md §5.2). An empty list means valid.
 */
@Component
public class SchemaValidator {

    private final JsonSchemaFactory factory =
            JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V202012);

    public List<String> validate(JsonNode schemaNode, JsonNode data) {
        JsonSchema schema = factory.getSchema(schemaNode);
        Set<ValidationMessage> messages = schema.validate(data);
        return messages.stream().map(ValidationMessage::getMessage).toList();
    }
}
