package com.handbook.fundamentals.solid;

import com.handbook.fundamentals.solid.before.PaymentProcessor;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class PaymentProcessorBeforeTest {

    @Test
    void processesKnownPaymentTypes() {
        PaymentProcessor processor = new PaymentProcessor();

        String receipt = processor.process("CREDIT_CARD", 100.0);

        assertTrue(receipt.contains("CREDIT_CARD"));
        assertEquals(1, processor.processedCount());
        assertEquals(100.0, processor.totalProcessed());
    }

    @Test
    void rejectsUnknownPaymentTypeWithNoExtensionPointAvailable() {
        PaymentProcessor processor = new PaymentProcessor();

        // This is the OCP violation made concrete: there is no way to
        // support a new "CRYPTO" payment type without editing
        // PaymentProcessor.process() itself. Contrast with
        // OpenClosedPrincipleTest (in the `after` package), which adds a
        // brand-new payment method with ZERO changes to the processor class.
        IllegalArgumentException ex = assertThrows(IllegalArgumentException.class,
                () -> processor.process("CRYPTO", 50.0));
        assertTrue(ex.getMessage().contains("editing this method directly"));
    }
}
