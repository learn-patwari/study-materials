package com.relay.engine;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ConditionEvaluatorTest {

    private final ConditionEvaluator eval = new ConditionEvaluator();

    @Test
    void numericComparisons() {
        assertThat(eval.evaluate("2499 > 1000")).isTrue();
        assertThat(eval.evaluate("10 <= 10")).isTrue();
        assertThat(eval.evaluate("3 >= 4")).isFalse();
        assertThat(eval.evaluate("5 == 5")).isTrue();
        assertThat(eval.evaluate("5 != 6")).isTrue();
    }

    @Test
    void stringEquality() {
        assertThat(eval.evaluate("APPROVED == APPROVED")).isTrue();
        assertThat(eval.evaluate("'a' != 'b'")).isTrue();
    }

    @Test
    void unparseableThrows() {
        assertThatThrownBy(() -> eval.evaluate("totally not an expression"))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
