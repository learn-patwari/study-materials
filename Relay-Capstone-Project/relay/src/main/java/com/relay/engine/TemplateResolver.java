package com.relay.engine;

import com.fasterxml.jackson.databind.JsonNode;
import org.springframework.stereotype.Component;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Resolves {@code {{path}}} templates in strings against a scope JsonNode.
 * Paths are dotted, e.g. {@code input.orderId} or {@code fetch_order.amount}.
 * A missing path throws (typed error, never a silent blank) — see 05-Node-Executors.md §5.1.
 */
@Component
public class TemplateResolver {

    private static final Pattern TEMPLATE = Pattern.compile("\\{\\{\\s*([^}]+?)\\s*}}");

    public String resolve(String template, JsonNode scope) {
        if (template == null) return null;
        Matcher m = TEMPLATE.matcher(template);
        StringBuilder sb = new StringBuilder();
        while (m.find()) {
            String path = m.group(1);
            JsonNode value = navigate(scope, path);
            if (value == null || value.isMissingNode()) {
                throw new IllegalArgumentException("template path not found: '" + path + "'");
            }
            m.appendReplacement(sb, Matcher.quoteReplacement(value.asText()));
        }
        m.appendTail(sb);
        return sb.toString();
    }

    private JsonNode navigate(JsonNode scope, String path) {
        JsonNode current = scope;
        for (String part : path.split("\\.")) {
            if (current == null) return null;
            current = current.get(part);
        }
        return current;
    }
}
