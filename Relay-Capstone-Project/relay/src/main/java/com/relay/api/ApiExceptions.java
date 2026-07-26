package com.relay.api;

import java.util.List;

/** API-layer exceptions with their intended HTTP semantics. */
public final class ApiExceptions {

    private ApiExceptions() {}

    /** 404 */
    public static class NotFoundException extends RuntimeException {
        public NotFoundException(String message) { super(message); }
    }

    /** 409 — definition/publish validation failed; carries the list of issues. */
    public static class ValidationException extends RuntimeException {
        private final List<String> issues;
        public ValidationException(String message, List<String> issues) {
            super(message);
            this.issues = issues == null ? List.of() : issues;
        }
        public List<String> getIssues() { return issues; }
    }

    /** 400 — bad request (e.g., no published version, malformed body). */
    public static class BadRequestException extends RuntimeException {
        public BadRequestException(String message) { super(message); }
    }

    /** 401 — webhook HMAC verification failed. */
    public static class UnauthorizedException extends RuntimeException {
        public UnauthorizedException(String message) { super(message); }
    }
}
