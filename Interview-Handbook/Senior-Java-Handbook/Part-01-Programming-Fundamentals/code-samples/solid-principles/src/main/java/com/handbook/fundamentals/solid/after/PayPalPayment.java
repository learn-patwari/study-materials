package com.handbook.fundamentals.solid.after;

public final class PayPalPayment implements PaymentMethod {

    private final String email;

    public PayPalPayment(String email) {
        this.email = email;
    }

    @Override
    public Receipt pay(double amount) {
        if (amount <= 0) {
            throw new IllegalArgumentException("amount must be positive: " + amount);
        }
        return new Receipt("PAYPAL:" + email, amount, true);
    }
}
