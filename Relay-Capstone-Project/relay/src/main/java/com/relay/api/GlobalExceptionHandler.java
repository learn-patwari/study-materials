package com.relay.api;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.List;
import java.util.Map;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(ApiExceptions.NotFoundException.class)
    public ResponseEntity<Map<String, Object>> notFound(ApiExceptions.NotFoundException e) {
        return body(HttpStatus.NOT_FOUND, "not_found", e.getMessage(), null);
    }

    @ExceptionHandler(ApiExceptions.ValidationException.class)
    public ResponseEntity<Map<String, Object>> validation(ApiExceptions.ValidationException e) {
        return body(HttpStatus.CONFLICT, "validation_failed", e.getMessage(), e.getIssues());
    }

    @ExceptionHandler(ApiExceptions.BadRequestException.class)
    public ResponseEntity<Map<String, Object>> badRequest(ApiExceptions.BadRequestException e) {
        return body(HttpStatus.BAD_REQUEST, "bad_request", e.getMessage(), null);
    }

    @ExceptionHandler(ApiExceptions.UnauthorizedException.class)
    public ResponseEntity<Map<String, Object>> unauthorized(ApiExceptions.UnauthorizedException e) {
        return body(HttpStatus.UNAUTHORIZED, "unauthorized", e.getMessage(), null);
    }

    private ResponseEntity<Map<String, Object>> body(HttpStatus status, String error,
                                                     String message, List<String> issues) {
        Map<String, Object> b = new java.util.LinkedHashMap<>();
        b.put("error", error);
        b.put("message", message);
        if (issues != null) b.put("issues", issues);
        return ResponseEntity.status(status).body(b);
    }
}
