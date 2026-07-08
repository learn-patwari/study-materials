package com.handbook.urlshortener;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class Base62EncoderTest {

    @Test
    void encodesZeroAsSingleCharacter() {
        assertEquals("0", Base62Encoder.encode(0));
    }

    @ParameterizedTest
    @ValueSource(longs = {0, 1, 61, 62, 3843, 1_000_000, 3_521_614_606_207L})
    void roundTripsEncodeAndDecode(long id) {
        String code = Base62Encoder.encode(id);
        assertEquals(id, Base62Encoder.decode(code));
    }

    @Test
    void largerIdsProduceLexicographicallyLongerOrEqualCodes() {
        // Not a strict ordering guarantee (Base62 isn't order-preserving the
        // way zero-padded fixed-width encodings are), but code LENGTH must
        // never decrease as id increases -- this is what keeps the 7-char
        // code budget from silently overflowing.
        assertEquals(1, Base62Encoder.encode(0).length());
        assertEquals(1, Base62Encoder.encode(61).length());
        assertEquals(2, Base62Encoder.encode(62).length());
        assertEquals(2, Base62Encoder.encode(3843).length());
        assertEquals(3, Base62Encoder.encode(3844).length());
    }

    @Test
    void rejectsNegativeIds() {
        assertThrows(IllegalArgumentException.class, () -> Base62Encoder.encode(-1));
    }

    @Test
    void rejectsInvalidCharacterOnDecode() {
        assertThrows(IllegalArgumentException.class, () -> Base62Encoder.decode("abc!"));
    }

    @Test
    void rejectsEmptyCodeOnDecode() {
        assertThrows(IllegalArgumentException.class, () -> Base62Encoder.decode(""));
    }
}
