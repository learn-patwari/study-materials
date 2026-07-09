package com.handbook.fundamentals.solid.before;

/**
 * THE VIOLATION. To add a new payment type, you must edit this class's
 * {@code process()} method directly — every new payment type means a new
 * {@code else if} branch here, in a class that's already deployed and
 * tested. That's a violation of the <b>Open/Closed Principle</b>: this
 * class is not open for extension without modification.
 *
 * <p>It also violates the <b>Dependency Inversion Principle</b>: this
 * high-level policy class (payment processing) directly implements the
 * low-level charging details for each concrete payment type inline —
 * there is no abstraction between "process a payment" and "how a credit
 * card specifically gets charged."
 *
 * @see com.handbook.fundamentals.solid.after.PaymentProcessor for the fix.
 */
public final class PaymentProcessor {

    private int processedCount = 0;
    private double totalProcessed = 0.0;

    public String process(String paymentType, double amount) {
        if (amount <= 0) {
            throw new IllegalArgumentException("amount must be positive: " + amount);
        }

        String receipt;
        if ("CREDIT_CARD".equals(paymentType)) {
            // Credit card charging logic lives HERE, inline.
            receipt = "CREDIT_CARD charged " + amount;
        } else if ("PAYPAL".equals(paymentType)) {
            // PayPal charging logic ALSO lives here, inline.
            receipt = "PAYPAL charged " + amount;
        } else {
            throw new IllegalArgumentException("Unsupported payment type: " + paymentType
                    + " -- adding support requires editing this method directly.");
        }

        processedCount++;
        totalProcessed += amount;
        return receipt;
    }

    public int processedCount() {
        return processedCount;
    }

    public double totalProcessed() {
        return totalProcessed;
    }
}
