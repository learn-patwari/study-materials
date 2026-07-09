package com.handbook.fundamentals.cache;

/**
 * Two ways to sum every element of a 2D array — identical result, very
 * different cache behavior. Java stores a 2D array as an array of row
 * references ({@code int[][]} is really {@code int[]}-of-{@code int[]}),
 * so each row is contiguous in memory but rows themselves are not
 * guaranteed adjacent.
 *
 * <p>{@link #sumRowMajor} walks each row left-to-right before moving to the
 * next row — this matches the array's actual memory layout, so each cache
 * line fetched from RAM (typically 64 bytes = 16 {@code int}s) is fully
 * consumed before the next fetch. {@link #sumColumnMajor} walks straight
 * down a column first — every single access jumps to a different row
 * (a different, likely-uncached memory region), so almost every read misses
 * the cache and stalls on a full RAM fetch.
 */
public final class MatrixTraversal {

    private MatrixTraversal() {
    }

    public static long sumRowMajor(int[][] matrix) {
        long sum = 0;
        for (int[] row : matrix) {
            for (int value : row) {
                sum += value;
            }
        }
        return sum;
    }

    public static long sumColumnMajor(int[][] matrix) {
        long sum = 0;
        int rows = matrix.length;
        int cols = matrix.length == 0 ? 0 : matrix[0].length;
        for (int col = 0; col < cols; col++) {
            for (int row = 0; row < rows; row++) {
                sum += matrix[row][col];
            }
        }
        return sum;
    }
}
