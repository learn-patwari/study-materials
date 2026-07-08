package com.handbook.urlshortener;

/**
 * Encodes a non-negative long into a Base62 string ([0-9A-Za-z]) and back.
 * Base62 is the standard alphabet choice for URL shorteners: URL-safe with
 * no encoding needed (unlike Base64's '+' and '/'), and denser than Base36,
 * so a 7-character code covers 62^7 (~3.5 trillion) distinct IDs — enough
 * headroom for a system provisioned for billions of URLs without ever
 * needing to lengthen the code.
 */
public final class Base62Encoder {

    private static final String ALPHABET =
            "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
    private static final int BASE = ALPHABET.length();

    private Base62Encoder() {
    }

    public static String encode(long id) {
        if (id < 0) {
            throw new IllegalArgumentException("id must be non-negative: " + id);
        }
        if (id == 0) {
            return String.valueOf(ALPHABET.charAt(0));
        }
        StringBuilder sb = new StringBuilder();
        long remaining = id;
        while (remaining > 0) {
            int digit = (int) (remaining % BASE);
            sb.append(ALPHABET.charAt(digit));
            remaining /= BASE;
        }
        return sb.reverse().toString();
    }

    public static long decode(String code) {
        if (code == null || code.isEmpty()) {
            throw new IllegalArgumentException("code must not be null or empty");
        }
        long id = 0;
        for (int i = 0; i < code.length(); i++) {
            int digit = ALPHABET.indexOf(code.charAt(i));
            if (digit < 0) {
                throw new IllegalArgumentException("invalid Base62 character: " + code.charAt(i));
            }
            id = id * BASE + digit;
        }
        return id;
    }
}
