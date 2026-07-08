package com.handbook.urlshortener;

import java.util.Optional;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class UrlShortenerServiceTest {

    private final RangeBasedIdGenerator idGenerator = new RangeBasedIdGenerator();
    private final UrlRepository repository = new UrlRepository();
    private final UrlShortenerService service = new UrlShortenerService(idGenerator, repository);

    @Test
    void shortenThenResolveRoundTrips() {
        String longUrl = "https://example.com/some/very/long/path?query=param";

        String code = service.shorten(longUrl);
        Optional<String> resolved = service.resolve(code);

        assertTrue(resolved.isPresent());
        assertEquals(longUrl, resolved.get());
    }

    @Test
    void resolvingUnknownCodeReturnsEmpty() {
        assertTrue(service.resolve("doesNotExist").isEmpty());
    }

    @Test
    void rejectsMalformedUrl() {
        assertThrows(IllegalArgumentException.class, () -> service.shorten("not a url"));
    }

    @Test
    void rejectsBlankUrl() {
        assertThrows(IllegalArgumentException.class, () -> service.shorten("   "));
    }

    @Test
    void distinctLongUrlsGetDistinctCodes() {
        String codeA = service.shorten("https://example.com/a");
        String codeB = service.shorten("https://example.com/b");

        assertTrue(!codeA.equals(codeB), "distinct URLs must not collide on the same code");
    }
}
