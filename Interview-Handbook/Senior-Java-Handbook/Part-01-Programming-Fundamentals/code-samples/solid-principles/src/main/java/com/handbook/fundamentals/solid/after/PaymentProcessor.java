package com.handbook.fundamentals.solid.after;

/**
 * THE FIX for {@code before.PaymentProcessor}: depends only on the {@link
 * PaymentMethod} abstraction, never on a concrete payment type. Adding a
 * brand-new payment method (see {@code OpenClosedPrincipleTest}) requires
 * zero changes to this class — it is open for extension, closed for
 * modification.
 */
public final class PaymentProcessor {

    private int processedCount = 0;
    private double totalProcessed = 0.0;

    public Receipt process(PaymentMethod method, double amount) {
        if (amount <= 0) {
            throw new IllegalArgumentException("amount must be positive: " + amount);
        }
        Receipt receipt = method.pay(amount);
        if (receipt.success()) {
            processedCount++;
            totalProcessed += amount;
        }
        return receipt;
    }

    public int processedCount() {
        return processedCount;
    }

    public double totalProcessed() {
        return totalProcessed;
    }
}
