package com.handbook.interview;

import java.math.BigDecimal;
import java.util.Currency;
import java.util.HashSet;
import java.util.Set;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ImmutableMoneyTest {

    private static final Currency USD = Currency.getInstance("USD");
    private static final Currency EUR = Currency.getInstance("EUR");

    @Test
    void addReturnsNewInstanceAndDoesNotMutateOperands() {
        ImmutableMoney five = new ImmutableMoney(new BigDecimal("5.00"), USD);
        ImmutableMoney three = new ImmutableMoney(new BigDecimal("3.00"), USD);

        ImmutableMoney sum = five.add(three);

        assertEquals(new BigDecimal("8.00"), sum.amount());
        assertNotSame(five, sum, "add() must return a new instance, not mutate `this`");
        assertEquals(new BigDecimal("5.00"), five.amount(), "original operand must be unchanged");
    }

    @Test
    void equalityIsByValueNotByScale() {
        // The classic BigDecimal trap: 2.0 and 2.00 differ in SCALE, so
        // BigDecimal.equals() alone would say they're unequal. ImmutableMoney
        // must not inherit that surprise.
        ImmutableMoney twoPointZero = new ImmutableMoney(new BigDecimal("2.0"), USD);
        ImmutableMoney twoPointZeroZero = new ImmutableMoney(new BigDecimal("2.00"), USD);

        assertEquals(twoPointZero, twoPointZeroZero);
        assertEquals(twoPointZero.hashCode(), twoPointZeroZero.hashCode(),
                "equal objects must have equal hashCodes -- required by the equals/hashCode contract");
    }

    @Test
    void differentCurrenciesAreNeverEqualEvenWithSameAmount() {
        ImmutableMoney tenUsd = new ImmutableMoney(BigDecimal.TEN, USD);
        ImmutableMoney tenEur = new ImmutableMoney(BigDecimal.TEN, EUR);

        assertTrue(!tenUsd.equals(tenEur));
    }

    @Test
    void honorsEqualsHashCodeContractInHashSet() {
        Set<ImmutableMoney> set = new HashSet<>();
        set.add(new ImmutableMoney(new BigDecimal("1.00"), USD));
        set.add(new ImmutableMoney(new BigDecimal("1.0"), USD)); // equal by value, different scale

        assertEquals(1, set.size(),
                "value-equal ImmutableMoney instances must collapse to one HashSet entry");
    }

    @Test
    void rejectsMismatchedCurrencyArithmetic() {
        ImmutableMoney tenUsd = new ImmutableMoney(BigDecimal.TEN, USD);
        ImmutableMoney fiveEur = new ImmutableMoney(BigDecimal.valueOf(5), EUR);

        assertThrows(IllegalArgumentException.class, () -> tenUsd.add(fiveEur));
    }
}
