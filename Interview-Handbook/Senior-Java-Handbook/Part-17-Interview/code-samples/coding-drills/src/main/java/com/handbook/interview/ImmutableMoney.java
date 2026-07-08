package com.handbook.interview;

import java.math.BigDecimal;
import java.util.Currency;
import java.util.Objects;

/**
 * Classic "design an immutable value object" whiteboard problem. Covers the
 * three follow-ups an interviewer almost always asks:
 * <ol>
 *   <li>Why {@code final} class, final fields, no setters, and defensive
 *       handling of any mutable input (not needed here since
 *       {@link BigDecimal}/{@link Currency} are themselves immutable — but
 *       say so out loud; don't just get lucky).</li>
 *   <li>Why {@code equals}/{@code hashCode} MUST be overridden together —
 *       violating the {@code equals}/{@code hashCode} contract breaks any
 *       use of this type as a {@code HashMap} key or in a {@code HashSet}.</li>
 *   <li>Why arithmetic methods return a NEW instance instead of mutating
 *       {@code this} — the entire point of immutability is that an existing
 *       reference can never change out from under a caller holding it.</li>
 * </ol>
 */
public final class ImmutableMoney {

    private final BigDecimal amount;
    private final Currency currency;

    public ImmutableMoney(BigDecimal amount, Currency currency) {
        this.amount = Objects.requireNonNull(amount, "amount");
        this.currency = Objects.requireNonNull(currency, "currency");
    }

    public BigDecimal amount() {
        return amount;
    }

    public Currency currency() {
        return currency;
    }

    /** Returns a NEW ImmutableMoney -- this instance is never mutated. */
    public ImmutableMoney add(ImmutableMoney other) {
        requireSameCurrency(other);
        return new ImmutableMoney(this.amount.add(other.amount), this.currency);
    }

    public ImmutableMoney subtract(ImmutableMoney other) {
        requireSameCurrency(other);
        return new ImmutableMoney(this.amount.subtract(other.amount), this.currency);
    }

    private void requireSameCurrency(ImmutableMoney other) {
        if (!this.currency.equals(other.currency)) {
            throw new IllegalArgumentException(
                    "currency mismatch: " + this.currency + " vs " + other.currency);
        }
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (!(o instanceof ImmutableMoney other)) {
            return false;
        }
        // compareTo, not equals, on BigDecimal: BigDecimal.equals() treats
        // 2.0 and 2.00 as UNEQUAL (differing scale) -- a well-known trap.
        // Monetary equality should be by value, not by scale.
        return this.amount.compareTo(other.amount) == 0
                && this.currency.equals(other.currency);
    }

    @Override
    public int hashCode() {
        // Must be derived the same way equality is checked: normalize scale
        // before hashing, or 2.0 and 2.00 (equal per compareTo above) would
        // hash differently -- violating the equals/hashCode contract.
        return Objects.hash(amount.stripTrailingZeros(), currency);
    }

    @Override
    public String toString() {
        return amount + " " + currency.getCurrencyCode();
    }
}
