package com.handbook.fundamentals.solid.after;

public final class CreditCardPayment implements PaymentMethod {

    private final String cardNumberLast4;

    public CreditCardPayment(String cardNumberLast4) {
        this.cardNumberLast4 = cardNumberLast4;
    }

    @Override
    public Receipt pay(double amount) {
        if (amount <= 0) {
            throw new IllegalArgumentException("amount must be positive: " + amount);
        }
        return new Receipt("CREDIT_CARD:" + cardNumberLast4, amount, true);
    }
}
