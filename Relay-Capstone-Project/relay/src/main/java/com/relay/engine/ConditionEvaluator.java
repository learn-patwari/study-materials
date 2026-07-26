package com.relay.engine;

import org.springframework.stereotype.Component;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Evaluates a simple, already-template-resolved boolean expression of the form
 * {@code <lhs> <op> <rhs>} where op is one of {@code > < >= <= == !=}.
 * Numeric comparison when both sides parse as numbers, else string comparison
 * (only == / != are meaningful for strings).
 */
@Component
public class ConditionEvaluator {

    private static final Pattern EXPR =
            Pattern.compile("^\\s*(.+?)\\s*(>=|<=|==|!=|>|<)\\s*(.+?)\\s*$");

    public boolean evaluate(String expr) {
        if (expr == null) throw new IllegalArgumentException("condition expr is null");
        Matcher m = EXPR.matcher(expr);
        if (!m.matches()) {
            throw new IllegalArgumentException("unparseable condition: '" + expr + "'");
        }
        String lhs = unquote(m.group(1));
        String op = m.group(2);
        String rhs = unquote(m.group(3));

        Double ln = tryNumber(lhs);
        Double rn = tryNumber(rhs);
        if (ln != null && rn != null) {
            int c = Double.compare(ln, rn);
            return switch (op) {
                case ">" -> c > 0;
                case "<" -> c < 0;
                case ">=" -> c >= 0;
                case "<=" -> c <= 0;
                case "==" -> c == 0;
                case "!=" -> c != 0;
                default -> throw new IllegalArgumentException("bad op " + op);
            };
        }
        // string comparison
        return switch (op) {
            case "==" -> lhs.equals(rhs);
            case "!=" -> !lhs.equals(rhs);
            default -> throw new IllegalArgumentException(
                    "operator '" + op + "' not supported for non-numeric operands");
        };
    }

    private Double tryNumber(String s) {
        try { return Double.parseDouble(s); } catch (NumberFormatException e) { return null; }
    }

    private String unquote(String s) {
        if (s.length() >= 2 && ((s.startsWith("\"") && s.endsWith("\"")) || (s.startsWith("'") && s.endsWith("'")))) {
            return s.substring(1, s.length() - 1);
        }
        return s;
    }
}
