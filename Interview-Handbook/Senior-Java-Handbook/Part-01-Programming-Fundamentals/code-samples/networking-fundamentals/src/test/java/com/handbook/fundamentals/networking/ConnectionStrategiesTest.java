package com.handbook.fundamentals.networking;

import java.net.URI;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertTrue;

class ConnectionStrategiesTest {

    private LocalHttpServer server;
    private URI baseUri;

    @BeforeEach
    void startServer() throws Exception {
        server = new LocalHttpServer();
        baseUri = URI.create("http://127.0.0.1:" + server.port() + "/");
    }

    @AfterEach
    void stopServer() {
        server.close();
    }

    @Test
    void newConnectionPerRequestReturnsCorrectResponsesForEveryRequest() throws Exception {
        // ConnectionStrategies.verify() throws IllegalStateException internally
        // if any response is wrong -- reaching this line at all IS the
        // correctness assertion, same pattern as Chapter 01.02's ConcurrentTaskRunner.
        long elapsed = ConnectionStrategies.newConnectionPerRequest(baseUri, 10);
        assertTrue(elapsed >= 0);
    }

    @Test
    void reusedConnectionReturnsCorrectResponsesForEveryRequest() throws Exception {
        long elapsed = ConnectionStrategies.reusedConnection(baseUri, 10);
        assertTrue(elapsed >= 0);
    }

    @Test
    void handlesASingleRequest() throws Exception {
        assertTrue(ConnectionStrategies.newConnectionPerRequest(baseUri, 1) >= 0);
        assertTrue(ConnectionStrategies.reusedConnection(baseUri, 1) >= 0);
    }
}
