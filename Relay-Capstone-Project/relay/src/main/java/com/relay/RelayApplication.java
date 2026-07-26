package com.relay;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * Relay — AI Workflow Orchestrator (capstone v1).
 *
 * <p>Boots the REST API (control plane) and the outbox-backed worker pool (data plane).
 */
@SpringBootApplication
@EnableScheduling
public class RelayApplication {
    public static void main(String[] args) {
        SpringApplication.run(RelayApplication.class, args);
    }
}
