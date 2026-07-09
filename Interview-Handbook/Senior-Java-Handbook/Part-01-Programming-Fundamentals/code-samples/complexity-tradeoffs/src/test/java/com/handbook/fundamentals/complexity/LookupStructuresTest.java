package com.handbook.fundamentals.complexity;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class LookupStructuresTest {

    @Test
    void listLookupFindsAddedValuesAndRejectsAbsentOnes() {
        ListLookup lookup = new ListLookup();
        lookup.add(1);
        lookup.add(2);
        lookup.add(3);

        assertTrue(lookup.contains(2));
        assertFalse(lookup.contains(99));
        assertEquals(3, lookup.size());
    }

    @Test
    void hashLookupFindsAddedValuesAndRejectsAbsentOnes() {
        HashLookup lookup = new HashLookup();
        lookup.add(1);
        lookup.add(2);
        lookup.add(3);

        assertTrue(lookup.contains(2));
        assertFalse(lookup.contains(99));
        assertEquals(3, lookup.size());
    }

    @Test
    void bothImplementationsAgreeOnMembershipForTheSameData() {
        ListLookup listLookup = new ListLookup();
        HashLookup hashLookup = new HashLookup();

        int[] values = {5, 17, 42, -3, 1000, 0};
        for (int v : values) {
            listLookup.add(v);
            hashLookup.add(v);
        }

        for (int probe = -10; probe <= 1010; probe += 17) {
            assertEquals(listLookup.contains(probe), hashLookup.contains(probe),
                    "both lookup structures must agree on membership for probe " + probe);
        }
    }
}
