package com.handbook.urlshortener;

import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * A @WebMvcTest slice only loads the web layer (controllers, filters,
 * @ControllerAdvice) -- it deliberately does NOT stand up @Service/@Repository
 * beans, which is exactly what makes it fast. UrlShortenerService is
 * mocked rather than real, so this test verifies HTTP-layer behavior
 * (status codes, headers, request/response mapping) in isolation from the
 * business logic already covered by UrlShortenerServiceTest.
 */
@WebMvcTest(UrlShortenerController.class)
class UrlShortenerControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private UrlShortenerService service;

    @Test
    void shortenReturns201WithGeneratedCode() throws Exception {
        when(service.shorten(anyString())).thenReturn("b7");

        mockMvc.perform(post("/api/urls")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"longUrl\":\"https://example.com/staff-engineer-handbook\"}"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.code").value("b7"))
                .andExpect(jsonPath("$.shortPath").value("/b7"));
    }

    @Test
    void redirectFoundReturns302WithLocationHeader() throws Exception {
        when(service.resolve("b7")).thenReturn(Optional.of("https://example.com/staff-engineer-handbook"));

        mockMvc.perform(get("/{code}", "b7"))
                .andExpect(status().isFound())
                .andExpect(header().string("Location", "https://example.com/staff-engineer-handbook"));
    }

    @Test
    void redirectingUnknownCodeReturns404() throws Exception {
        when(service.resolve("doesNotExist")).thenReturn(Optional.empty());

        mockMvc.perform(get("/{code}", "doesNotExist"))
                .andExpect(status().isNotFound());
    }

    @Test
    void shorteningMalformedUrlReturns400() throws Exception {
        when(service.shorten(anyString())).thenThrow(new IllegalArgumentException("longUrl is not a well-formed URL"));

        mockMvc.perform(post("/api/urls")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"longUrl\":\"not a url\"}"))
                .andExpect(status().isBadRequest());
    }
}
