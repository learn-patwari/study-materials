package com.relay.security;

import org.springframework.stereotype.Component;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;

/** Verifies webhook trigger authenticity via HMAC-SHA256 (see 06-Guardrails-and-Security.md §6.4). */
@Component
public class HmacVerifier {

    /** Compute {@code sha256=<hex>} over the raw body using the workflow secret. */
    public String sign(String secret, String rawBody) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            byte[] digest = mac.doFinal(rawBody.getBytes(StandardCharsets.UTF_8));
            return "sha256=" + HexFormat.of().formatHex(digest);
        } catch (Exception e) {
            throw new IllegalStateException("HMAC computation failed", e);
        }
    }

    /** Constant-time comparison of the provided signature header against the expected value. */
    public boolean verify(String secret, String rawBody, String providedSignature) {
        if (providedSignature == null) return false;
        String expected = sign(secret, rawBody);
        return MessageDigest.isEqual(
                expected.getBytes(StandardCharsets.UTF_8),
                providedSignature.getBytes(StandardCharsets.UTF_8));
    }
}
