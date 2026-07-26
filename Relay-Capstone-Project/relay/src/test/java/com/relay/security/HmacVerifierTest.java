package com.relay.security;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class HmacVerifierTest {

    private final HmacVerifier hmac = new HmacVerifier();

    @Test
    void signAndVerifyRoundTrip() {
        String secret = "topsecret";
        String body = "{\"orderId\":\"A-1001\"}";
        String sig = hmac.sign(secret, body);
        assertThat(sig).startsWith("sha256=");
        assertThat(hmac.verify(secret, body, sig)).isTrue();
    }

    @Test
    void tamperedBodyFailsVerification() {
        String secret = "topsecret";
        String sig = hmac.sign(secret, "{\"amount\":100}");
        assertThat(hmac.verify(secret, "{\"amount\":999}", sig)).isFalse();
    }

    @Test
    void wrongSecretFailsVerification() {
        String body = "{\"a\":1}";
        String sig = hmac.sign("secret-a", body);
        assertThat(hmac.verify("secret-b", body, sig)).isFalse();
    }

    @Test
    void nullSignatureFailsSafely() {
        assertThat(hmac.verify("s", "body", null)).isFalse();
    }
}
