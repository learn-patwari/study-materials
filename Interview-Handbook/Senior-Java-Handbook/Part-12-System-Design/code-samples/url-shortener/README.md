# Code samples — Chapter 12.01: Designing a Scalable URL Shortener

A Spring Boot 3.2 / Java 21 module implementing the core of the case
study's design: Base62 encoding, a range-based (ticket server pattern) ID
generator, an in-memory cache-aside repository standing in for the real
Redis + primary-DB pair, and a minimal REST API (`POST /api/urls`,
`GET /{code}`).

```bash
mvn -q compile   # compiles cleanly against Java 21 / Spring Boot 3.2.5
mvn -q test      # 24 JUnit 5 tests (unit + @WebMvcTest slice), all passing
```

| Class | Responsibility |
|---|---|
| `Base62Encoder` | Pure encode/decode between a `long` id and a `[0-9A-Za-z]` short code |
| `RangeBasedIdGenerator` | Lock-free ID allocation via pre-claimed blocks (the "ticket server" pattern) — see chapter Internal Working |
| `UrlRepository` | In-memory stand-in for the Redis-cache + primary-DB pair described in the chapter's Architecture |
| `UrlShortenerService` | Validation + orchestration (id → code → persist) |
| `UrlShortenerController` | `POST /api/urls` (create), `GET /{code}` (302 redirect, not 301 — see the code comment for why) |

`RangeBasedIdGeneratorTest` includes a concurrency test (8 threads × 500 IDs)
asserting zero duplicate IDs under real contention — this is the property
the whole "ticket server" design exists to guarantee without a DB round
trip per request.
