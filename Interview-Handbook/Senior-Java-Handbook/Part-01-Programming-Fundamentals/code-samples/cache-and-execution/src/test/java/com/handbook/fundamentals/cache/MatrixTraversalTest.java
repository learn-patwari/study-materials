package com.handbook.fundamentals.cache;

import java.util.Random;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class MatrixTraversalTest {

    @Test
    void rowMajorAndColumnMajorProduceTheIdenticalSum() {
        Random random = new Random(42);
        int[][] matrix = new int[50][37];
        for (int[] row : matrix) {
            for (int j = 0; j < row.length; j++) {
                row[j] = random.nextInt(1000) - 500;
            }
        }

        long rowMajorSum = MatrixTraversal.sumRowMajor(matrix);
        long columnMajorSum = MatrixTraversal.sumColumnMajor(matrix);

        assertEquals(rowMajorSum, columnMajorSum,
                "traversal order changes cache behavior, never the result");
    }

    @Test
    void handlesEmptyMatrix() {
        int[][] empty = new int[0][0];
        assertEquals(0, MatrixTraversal.sumRowMajor(empty));
        assertEquals(0, MatrixTraversal.sumColumnMajor(empty));
    }

    @Test
    void handlesSingleElementMatrix() {
        int[][] single = {{42}};
        assertEquals(42, MatrixTraversal.sumRowMajor(single));
        assertEquals(42, MatrixTraversal.sumColumnMajor(single));
    }
}
