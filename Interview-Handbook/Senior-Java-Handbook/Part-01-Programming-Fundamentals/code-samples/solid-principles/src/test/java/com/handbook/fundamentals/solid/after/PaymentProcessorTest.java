package com.handbook.fundamentals.solid.after;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class PaymentProcessorTest {

    @Test
    void processesCreditCardPayment() {
        PaymentProcessor processor = new PaymentProcessor();

        Receipt receipt = processor.process(new CreditCardPayment("4242"), 100.0);

        assertTrue(receipt.success());
        assertEquals(100.0, receipt.amount());
        assertTrue(receipt.method().contains("CREDIT_CARD"));
    }

    @Test
    void processesPayPalPayment() {
        PaymentProcessor processor = new PaymentProcessor();

        Receipt receipt = processor.process(new PayPalPayment("buyer@example.com"), 75.5);

        assertTrue(receipt.success());
        assertEquals(75.5, receipt.amount());
        assertTrue(receipt.method().contains("PAYPAL"));
    }

    @Test
    void tracksProcessedCountAndTotalAcrossDifferentPaymentMethods() {
        PaymentProcessor processor = new PaymentProcessor();

        processor.process(new CreditCardPayment("1111"), 100.0);
        processor.process(new PayPalPayment("a@b.com"), 50.0);

        assertEquals(2, processor.processedCount());
        assertEquals(150.0, processor.totalProcessed());
    }

    @Test
    void rejectsNonPositiveAmountBeforeDelegatingToThePaymentMethod() {
        PaymentProcessor processor = new PaymentProcessor();

        assertThrows(IllegalArgumentException.class,
                () -> processor.process(new CreditCardPayment("4242"), 0.0));
        assertThrows(IllegalArgumentException.class,
                () -> processor.process(new CreditCardPayment("4242"), -10.0));
        assertEquals(0, processor.processedCount(), "rejected attempts must not count as processed");
    }
}
