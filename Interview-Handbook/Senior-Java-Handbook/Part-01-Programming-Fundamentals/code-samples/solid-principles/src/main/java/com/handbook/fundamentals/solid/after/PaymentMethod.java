package com.handbook.fundamentals.solid.after;

/**
 * THE FIX's abstraction. {@link PaymentProcessor} depends only on this
 * interface, never on a concrete payment type — this is the abstraction
 * that both the high-level policy (the processor) and the low-level
 * details (each concrete payment method) depend on, satisfying the
 * Dependency Inversion Principle. It's also what makes the processor open
 * for extension: any new class implementing this interface works with the
 * existing, unmodified {@link PaymentProcessor} (see {@code
 * OpenClosedPrincipleTest}).
 */
public interface PaymentMethod {
    Receipt pay(double amount);
}
