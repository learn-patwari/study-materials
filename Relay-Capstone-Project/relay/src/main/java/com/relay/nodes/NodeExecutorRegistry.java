package com.relay.nodes;

import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

/** Maps node {@code type} → executor (Factory). Adding a node type is a new bean, nothing else. */
@Component
public class NodeExecutorRegistry {

    private final Map<String, NodeExecutor> byType;

    public NodeExecutorRegistry(List<NodeExecutor> executors) {
        this.byType = executors.stream()
                .collect(Collectors.toMap(NodeExecutor::type, Function.identity()));
    }

    public NodeExecutor get(String type) {
        NodeExecutor e = byType.get(type);
        if (e == null) throw new IllegalArgumentException("no executor for node type '" + type + "'");
        return e;
    }
}
