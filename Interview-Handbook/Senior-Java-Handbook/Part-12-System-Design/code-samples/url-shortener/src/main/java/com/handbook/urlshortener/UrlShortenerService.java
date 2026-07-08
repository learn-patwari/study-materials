package com.handbook.urlshortener;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.Optional;
import org.springframework.stereotype.Service;

@Service
public class UrlShortenerService {

    private final RangeBasedIdGenerator idGenerator;
    private final UrlRepository repository;

    public UrlShortenerService(RangeBasedIdGenerator idGenerator, UrlRepository repository) {
        this.idGenerator = idGenerator;
        this.repository = repository;
    }

    /**
     * Shortens a long URL, returning the generated Base62 code. Validates the
     * input is a well-formed absolute URL before spending an ID on it — a
     * malformed URL should fail fast at write time, not silently produce a
     * dead short link discovered only when someone clicks it.
     */
    public String shorten(String longUrl) {
        validate(longUrl);
        long id = idGenerator.nextId();
        String code = Base62Encoder.encode(id);
        repository.save(code, longUrl);
        return code;
    }

    public Optional<String> resolve(String code) {
        return repository.findLongUrl(code);
    }

    private void validate(String longUrl) {
        if (longUrl == null || longUrl.isBlank()) {
            throw new IllegalArgumentException("longUrl must not be blank");
        }
        try {
            URI uri = new URI(longUrl);
            if (!uri.isAbsolute()) {
                throw new IllegalArgumentException("longUrl must be absolute (include a scheme): " + longUrl);
            }
        } catch (URISyntaxException e) {
            throw new IllegalArgumentException("longUrl is not a well-formed URL: " + longUrl, e);
        }
    }
}
