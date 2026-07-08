package com.handbook.jvm;

import java.lang.management.ManagementFactory;
import java.lang.management.MemoryPoolMXBean;
import java.lang.management.MemoryUsage;
import java.util.List;

/**
 * Prints the live memory pools the JVM is actually running with (Eden,
 * Survivor, Old Gen / Tenured, Metaspace, and — on G1/ZGC — the collector's
 * own region-based pools) using {@link java.lang.management.MemoryPoolMXBean},
 * the same MXBean {@code jconsole} and {@code jcmd VM.native_memory} read from.
 *
 * <p>Run it with different collectors to see the pool names change:
 * <pre>
 *   java -XX:+UseG1GC -cp target/classes com.handbook.jvm.MemoryPoolsReporter
 *   java -XX:+UseZGC  -cp target/classes com.handbook.jvm.MemoryPoolsReporter
 * </pre>
 */
public final class MemoryPoolsReporter {

    private MemoryPoolsReporter() {
    }

    public static void main(String[] args) {
        System.out.println(report());
    }

    /** Package-private for testability — returns the report as a string instead of printing it. */
    static String report() {
        List<MemoryPoolMXBean> pools = ManagementFactory.getMemoryPoolMXBeans();
        StringBuilder sb = new StringBuilder();
        sb.append(String.format("%-28s %-10s %12s %12s %12s%n",
                "Pool", "Type", "Used(MB)", "Committed(MB)", "Max(MB)"));
        for (MemoryPoolMXBean pool : pools) {
            MemoryUsage usage = pool.getUsage();
            sb.append(String.format("%-28s %-10s %12.1f %12.1f %12s%n",
                    pool.getName(),
                    pool.getType(),
                    toMb(usage.getUsed()),
                    toMb(usage.getCommitted()),
                    usage.getMax() < 0 ? "unbounded" : String.format("%.1f", toMb(usage.getMax()))));
        }
        return sb.toString();
    }

    private static double toMb(long bytes) {
        return bytes / (1024.0 * 1024.0);
    }
}
