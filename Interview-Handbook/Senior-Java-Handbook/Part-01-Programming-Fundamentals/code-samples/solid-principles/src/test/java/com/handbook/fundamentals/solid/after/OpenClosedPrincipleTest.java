package com.handbook.fundamentals.solid.after;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Proves the Open/Closed Principle claim concretely, not just by
 * assertion: a brand-new payment method ({@code CryptoPayment}, defined
 * ONLY inside this test file) is processed correctly by the existing,
 * completely UNMODIFIED {@link PaymentProcessor} class. Zero changes to
 * {@code PaymentProcessor.java} were needed to support it.
 *
 * <p>Contrast with {@code PaymentProcessorBeforeTest
 * .rejectsUnknownPaymentTypeWithNoExtensionPointAvailable}, where the
 * {@code before} version has no such extension point and throws instead.
 */
class OpenClosedPrincipleTest {

    /** A brand-new payment method, added without touching PaymentProcessor at all. */
    private static final class CryptoPayment implements PaymentMethod {
        private final String walletAddress;

        CryptoPayment(String walletAddress) {
            this.walletAddress = walletAddress;
        }

        @Override
        public Receipt pay(double amount) {
            if (amount <= 0) {
                throw new IllegalArgumentException("amount must be positive: " + amount);
            }
            return new Receipt("CRYPTO:" + walletAddress, amount, true);
        }
    }

    @Test
    void existingUnmodifiedProcessorSupportsABrandNewPaymentMethod() {
        PaymentProcessor processor = new PaymentProcessor();

        Receipt receipt = processor.process(new CryptoPayment("0xABC123"), 250.0);

        assertTrue(receipt.success());
        assertEquals(250.0, receipt.amount());
        assertEquals(1, processor.processedCount(),
                "PaymentProcessor.java was not modified to support CryptoPayment -- "
                        + "this is the Open/Closed Principle in action");
    }
}
