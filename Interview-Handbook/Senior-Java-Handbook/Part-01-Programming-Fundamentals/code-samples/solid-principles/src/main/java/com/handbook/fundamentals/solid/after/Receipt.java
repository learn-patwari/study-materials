package com.handbook.fundamentals.solid.after;

/** Immutable result of a payment attempt. See Chapter 17.01's {@code ImmutableMoney} for the same immutability rationale applied to money specifically. */
public record Receipt(String method, double amount, boolean success) {
}
