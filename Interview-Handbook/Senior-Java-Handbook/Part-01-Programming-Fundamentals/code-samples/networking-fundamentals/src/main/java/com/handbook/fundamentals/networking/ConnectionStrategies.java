package com.handbook.fundamentals.networking;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

/**
 * Two ways to make N HTTP requests to the same server — identical
 * responses, very different connection-setup cost. {@link
 * #newConnectionPerRequest} constructs a brand-new {@link HttpClient} (and
 * therefore an empty connection pool) for every request, forcing a fresh
 * TCP handshake each time. {@link #reusedConnection} constructs ONE {@code
 * HttpClient} and reuses it across all requests, letting the JDK's HTTP
 * client keep the underlying connection alive (HTTP/1.1 keep-alive) and
 * reuse it — this is exactly what a properly configured production HTTP
 * client (a shared, pooled client instance) does by default.
 */
public final class ConnectionStrategies {

    private ConnectionStrategies() {
    }

    public static long newConnectionPerRequest(URI baseUri, int requestCount) throws IOException, InterruptedException {
        long startNanos = System.nanoTime();
        for (int i = 0; i < requestCount; i++) {
            HttpClient client = HttpClient.newHttpClient(); // fresh client -> empty pool -> fresh connection
            HttpRequest request = HttpRequest.newBuilder(baseUri).GET().build();
            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
            verify(response);
        }
        return (System.nanoTime() - startNanos) / 1_000_000;
    }

    public static long reusedConnection(URI baseUri, int requestCount) throws IOException, InterruptedException {
        HttpClient client = HttpClient.newHttpClient();
        long startNanos = System.nanoTime();
        for (int i = 0; i < requestCount; i++) {
            HttpRequest request = HttpRequest.newBuilder(baseUri).GET().build();
            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
            verify(response);
        }
        return (System.nanoTime() - startNanos) / 1_000_000;
    }

    private static void verify(HttpResponse<String> response) {
        if (response.statusCode() != 200 || !"OK".equals(response.body())) {
            throw new IllegalStateException(
                    "unexpected response: " + response.statusCode() + " " + response.body());
        }
    }
}
