package com.handbook.fundamentals.os;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Random;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import static org.junit.jupiter.api.Assertions.assertEquals;

class BufferedIoDemoTest {

    @Test
    void bufferedAndUnbufferedReadsProduceTheIdenticalChecksum(@TempDir Path tempDir) throws IOException {
        Path file = tempDir.resolve("test-data.bin");
        byte[] data = new byte[10_000];
        new Random(99).nextBytes(data);
        Files.write(file, data);

        long expectedChecksum = 0;
        for (byte b : data) {
            expectedChecksum += (b & 0xFF); // match InputStream.read()'s unsigned-byte semantics
        }

        assertEquals(expectedChecksum, BufferedIoDemo.readAllBytesUnbuffered(file));
        assertEquals(expectedChecksum, BufferedIoDemo.readAllBytesBuffered(file));
    }

    @Test
    void handlesEmptyFile(@TempDir Path tempDir) throws IOException {
        Path file = tempDir.resolve("empty.bin");
        Files.write(file, new byte[0]);

        assertEquals(0, BufferedIoDemo.readAllBytesUnbuffered(file));
        assertEquals(0, BufferedIoDemo.readAllBytesBuffered(file));
    }
}
