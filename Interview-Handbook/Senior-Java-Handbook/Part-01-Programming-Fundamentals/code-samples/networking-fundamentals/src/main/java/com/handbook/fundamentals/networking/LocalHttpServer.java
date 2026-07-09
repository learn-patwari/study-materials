package com.handbook.fundamentals.networking;

import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;

/**
 * A minimal local HTTP/1.1 server (JDK-builtin {@code
 * com.sun.net.httpserver.HttpServer}, no external dependencies) bound to
 * an ephemeral loopback port, so this chapter's connection-reuse
 * comparison runs fully offline. Always responds {@code 200 OK} with a
 * fixed body — the point of this chapter's demo is connection setup cost,
 * not request routing or business logic.
 */
public final class LocalHttpServer implements AutoCloseable {

    private final HttpServer server;

    public LocalHttpServer() throws IOException {
        this.server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", exchange -> {
            byte[] body = "OK".getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200, body.length);
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(body);
            }
        });
        server.setExecutor(null); // default sequential executor -- fine for this demo's request volume
        server.start();
    }

    public int port() {
        return server.getAddress().getPort();
    }

    @Override
    public void close() {
        server.stop(0);
    }
}
