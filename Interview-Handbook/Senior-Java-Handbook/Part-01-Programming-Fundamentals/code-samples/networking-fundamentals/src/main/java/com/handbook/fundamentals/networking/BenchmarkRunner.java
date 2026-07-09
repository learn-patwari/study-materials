package com.handbook.fundamentals.networking;

import java.net.URI;

/**
 * Manual timing demonstration for the connection-reuse comparison in this
 * package. Not run as part of the JUnit suite -- see Chapter 01.01's
 * {@code BenchmarkRunner} for the same rationale.
 *
 * <pre>
 *   mvn -q compile
 *   java -cp target/classes com.handbook.fundamentals.networking.BenchmarkRunner
 * </pre>
 */
public final class BenchmarkRunner {

    private BenchmarkRunner() {
    }

    public static void main(String[] args) throws Exception {
        int requestCount = 300;

        try (LocalHttpServer server = new LocalHttpServer()) {
            URI baseUri = URI.create("http://127.0.0.1:" + server.port() + "/");

            long newConnEachTime = ConnectionStrategies.newConnectionPerRequest(baseUri, requestCount);
            long reused = ConnectionStrategies.reusedConnection(baseUri, requestCount);

            System.out.println("Connection strategy demo (" + requestCount + " requests to a local server):");
            System.out.println("  New connection per request: " + newConnEachTime + " ms");
            System.out.println("  Reused (keep-alive) connection: " + reused + " ms");
            System.out.println("  (Reused connection avoids a fresh TCP handshake -- and in production, "
                    + "a fresh TLS handshake -- on every single request.)");
        }
    }
}
