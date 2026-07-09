package com.handbook.fundamentals.patterns.decorator;

import java.util.Optional;

/**
 * The abstraction every decorator in this package wraps. Note the
 * resemblance to Chapter 01.04's {@code PaymentMethod} interface — both
 * are "depend on the abstraction, not the concrete implementation," the
 * Dependency Inversion Principle. Decorator adds a further idea on top:
 * an implementation of this SAME interface can wrap ANOTHER implementation
 * of it, adding behavior transparently to callers.
 */
public interface UserRepository {
    Optional<String> findById(String id);
}
