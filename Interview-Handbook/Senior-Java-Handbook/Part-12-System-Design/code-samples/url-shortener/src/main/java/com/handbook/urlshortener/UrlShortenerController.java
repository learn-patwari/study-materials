package com.handbook.urlshortener;

import java.net.URI;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class UrlShortenerController {

    private final UrlShortenerService service;

    public UrlShortenerController(UrlShortenerService service) {
        this.service = service;
    }

    @PostMapping("/api/urls")
    public ResponseEntity<ShortenResponse> shorten(@RequestBody ShortenRequest request) {
        String code = service.shorten(request.longUrl());
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(new ShortenResponse(code, "/" + code));
    }

    /**
     * 302 (not 301) is deliberate: a permanent redirect gets cached by
     * browsers/CDNs indefinitely, silently defeating click-analytics on this
     * short code for every subsequent visit from that client. A temporary
     * redirect keeps every click hitting this service, which is required if
     * the product needs accurate click counts (see Production Examples).
     */
    @GetMapping("/{code}")
    @ResponseStatus(HttpStatus.FOUND)
    public ResponseEntity<Void> redirect(@PathVariable String code) {
        return service.resolve(code)
                .map(longUrl -> ResponseEntity.status(HttpStatus.FOUND)
                        .location(URI.create(longUrl))
                        .<Void>build())
                .orElseGet(() -> ResponseEntity.notFound().build());
    }

    @ExceptionHandler(IllegalArgumentException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public String handleInvalidUrl(IllegalArgumentException e) {
        return e.getMessage();
    }

    public record ShortenRequest(String longUrl) {
    }

    public record ShortenResponse(String code, String shortPath) {
    }
}
