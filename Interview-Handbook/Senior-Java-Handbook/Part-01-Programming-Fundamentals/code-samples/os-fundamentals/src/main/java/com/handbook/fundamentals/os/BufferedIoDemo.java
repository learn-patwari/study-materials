package com.handbook.fundamentals.os;

import java.io.BufferedInputStream;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Path;

/**
 * Reads a file byte-by-byte two ways: raw/unbuffered (each {@code read()}
 * call on a plain {@link FileInputStream} crosses into the kernel to
 * fetch data, in the worst case one syscall per byte) vs. through a
 * {@link BufferedInputStream} (which reads in large internal chunks via
 * far fewer syscalls, then serves individual byte requests from that
 * in-memory buffer). Same result, very different number of user/kernel
 * boundary crossings — see this chapter's Internal Working section for
 * why that boundary is expensive.
 */
public final class BufferedIoDemo {

    private BufferedIoDemo() {
    }

    public static long readAllBytesUnbuffered(Path file) throws IOException {
        long checksum = 0;
        try (InputStream in = new FileInputStream(file.toFile())) {
            int b;
            while ((b = in.read()) != -1) {
                checksum += b;
            }
        }
        return checksum;
    }

    public static long readAllBytesBuffered(Path file) throws IOException {
        long checksum = 0;
        try (InputStream in = new BufferedInputStream(new FileInputStream(file.toFile()))) {
            int b;
            while ((b = in.read()) != -1) {
                checksum += b;
            }
        }
        return checksum;
    }
}
