package com.star.rag.bench;

import com.star.rag.TestVecDll;
import com.star.rag.store.SQLiteVecStore;
import com.star.rag.store.VectorStore;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.Random;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

// 混合检索热路径压测：5000 块语料 + 单线程/8 并发查询。
// 只在显式开启时运行：RAG_BENCH=true mvn -pl rag-mcp -Dtest=HybridSearchBenchmarkTest test
@EnabledIfEnvironmentVariable(named = "RAG_BENCH", matches = "true")
class HybridSearchBenchmarkTest {

    private static final int CHUNKS = 5000;
    private static final int QUERIES = 2000;
    private static final int CONCURRENCY = 8;
    private static final int DIMS = 1024;

    @Test
    void benchmark() throws Exception {
        Random random = new Random(42);
        SQLiteVecStore store = new SQLiteVecStore(":memory:", TestVecDll.path());
        List<String> contents = new ArrayList<>();
        List<float[]> vectors = new ArrayList<>();
        for (int i = 0; i < CHUNKS; i++) {
            String content = "城市" + (i % 34) + " 区" + (i % 20) + " 小区" + i
                    + " 一室一厅 租金" + (3000 + i % 5000) + "元";
            float[] vector = new float[DIMS];
            for (int d = 0; d < 8; d++) {
                vector[random.nextInt(DIMS)] = random.nextFloat();
            }
            contents.add(content);
            vectors.add(vector);
            store.insertChunk("system", SQLiteVecStore.SHARED_KB_ID, content, "bench.txt", vector, "{}");
        }

        // 预热
        for (int i = 0; i < 200; i++) {
            store.search("system", SQLiteVecStore.SHARED_KB_ID,
                    "城市" + (i % 34) + " 小区" + (i % CHUNKS),
                    vectors.get(i % CHUNKS), 5, 1.5);
        }

        long[] single = new long[QUERIES];
        long singleStart = System.nanoTime();
        for (int i = 0; i < QUERIES; i++) {
            int idx = random.nextInt(CHUNKS);
            long start = System.nanoTime();
            store.search("system", SQLiteVecStore.SHARED_KB_ID,
                    "城市" + (idx % 34) + " 小区" + idx, vectors.get(idx), 5, 1.5);
            single[i] = System.nanoTime() - start;
        }
        long singleNanos = System.nanoTime() - singleStart;

        long[] concurrent = new long[QUERIES];
        AtomicInteger cursor = new AtomicInteger();
        CountDownLatch start = new CountDownLatch(1);
        CountDownLatch done = new CountDownLatch(CONCURRENCY);
        ExecutorService pool = Executors.newFixedThreadPool(CONCURRENCY);
        long concurrentStart;
        for (int t = 0; t < CONCURRENCY; t++) {
            pool.submit(() -> {
                try {
                    start.await();
                    while (true) {
                        int i = cursor.getAndIncrement();
                        if (i >= QUERIES) {
                            break;
                        }
                        int idx = i % CHUNKS;
                        long s = System.nanoTime();
                        store.search("system", SQLiteVecStore.SHARED_KB_ID,
                                "城市" + (idx % 34) + " 小区" + idx, vectors.get(idx), 5, 1.5);
                        concurrent[i] = System.nanoTime() - s;
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                } finally {
                    done.countDown();
                }
            });
        }
        concurrentStart = System.nanoTime();
        start.countDown();
        done.await(5, TimeUnit.MINUTES);
        long concurrentNanos = System.nanoTime() - concurrentStart;
        pool.shutdownNow();
        store.close();

        System.out.println("RAG_BENCH chunks=" + CHUNKS + " queries=" + QUERIES);
        System.out.println("RAG_BENCH single " + summary(single, singleNanos));
        System.out.println("RAG_BENCH concurrent=" + CONCURRENCY + " " + summary(concurrent, concurrentNanos));
    }

    private String summary(long[] latencies, long totalNanos) {
        long[] sorted = latencies.clone();
        Arrays.sort(sorted);
        double qps = latencies.length / (totalNanos / 1_000_000_000.0);
        return String.format(Locale.ROOT,
                "qps=%.1f p50=%.2fms p95=%.2fms p99=%.2fms",
                qps, pct(sorted, 50) / 1_000_000.0, pct(sorted, 95) / 1_000_000.0,
                pct(sorted, 99) / 1_000_000.0);
    }

    private long pct(long[] sorted, int pct) {
        int index = (int) Math.ceil(sorted.length * pct / 100.0) - 1;
        return sorted[Math.max(0, Math.min(sorted.length - 1, index))];
    }
}
