package com.star.rag.eval;

import com.star.rag.TestVecDll;
import com.star.rag.embedding.EmbeddingClient;
import com.star.rag.store.SQLiteVecStore;
import com.star.rag.store.VectorStore;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;

import java.nio.charset.StandardCharsets;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

// RAG 评测：用真实房源语料 + DashScope 真实 embedding，比较纯向量与混合检索。
// 只在显式开启时运行，避免 CI/日常构建产生外部调用：
//   RAG_EVAL=true DASHSCOPE_API_KEY=xxx mvn -pl rag-mcp -Dtest=RagEvaluationTest test
@EnabledIfEnvironmentVariable(named = "RAG_EVAL", matches = "true")
@EnabledIfEnvironmentVariable(named = "DASHSCOPE_API_KEY", matches = ".+")
class RagEvaluationTest {

    private static final Pattern PRICE = Pattern.compile("(\\d{3,6})\\s*元");
    private static final int TOP_K = 5;

    record Listing(String city, String content, int price) {
    }

    record Query(String city, String text, int budget) {
    }

    record ExactQuery(String city, String text, String token) {
    }

    record Result(int queries, int city1, int city3, int city5, int budget5,
                  int relevant, int retrieved, double mrr, long avgMicros) {
        String line() {
            return String.format(Locale.ROOT,
                    "queries=%d cityRecall@1=%.1f%% cityRecall@3=%.1f%% cityRecall@5=%.1f%% "
                            + "budgetHit@5=%.1f%% precision@5=%.1f%% mrr=%.3f avg=%.2fms",
                    queries, 100.0 * city1 / queries, 100.0 * city3 / queries, 100.0 * city5 / queries,
                    100.0 * budget5 / queries, 100.0 * relevant / Math.max(1, retrieved),
                    mrr / queries, avgMicros / 1000.0);
        }
    }

    record ExactResult(int queries, int hit1, int hit3, int hit5,
                       int relevant, int retrieved, double mrr, long avgMicros) {
        String line() {
            return String.format(Locale.ROOT,
                    "queries=%d exactHit@1=%.1f%% exactHit@3=%.1f%% exactHit@5=%.1f%% "
                            + "precision@5=%.1f%% mrr=%.3f avg=%.2fms",
                    queries, 100.0 * hit1 / queries, 100.0 * hit3 / queries, 100.0 * hit5 / queries,
                    100.0 * relevant / Math.max(1, retrieved), mrr / queries, avgMicros / 1000.0);
        }
    }

    @Test
    void evaluate() throws Exception {
        String apiKey = System.getenv("DASHSCOPE_API_KEY");
        Path housesDir = findHousesDir();
        List<Listing> listings = load(housesDir);
        if (listings.isEmpty()) {
            throw new IllegalStateException("房源语料为空: " + housesDir);
        }

        EmbeddingClient embedding = new EmbeddingClient(apiKey);
        List<float[]> vectors = embedding.embedBatch(listings.stream().map(Listing::content).toList(), 10);

        SQLiteVecStore store = new SQLiteVecStore(":memory:", TestVecDll.path());
        Map<String, Listing> byContent = new HashMap<>();
        for (int i = 0; i < listings.size(); i++) {
            Listing listing = listings.get(i);
            store.insertChunk("system", SQLiteVecStore.SHARED_KB_ID, listing.content(),
                    listing.city() + ".txt", vectors.get(i), "{}");
            byContent.put(listing.content(), listing);
        }

        List<Query> queries = buildQueries(listings);
        List<float[]> queryVectors = embedding.embedBatch(queries.stream().map(Query::text).toList(), 10);

        Result vectorOnly = evaluate(store, queries, queryVectors, byContent, false);
        Result hybrid = evaluate(store, queries, queryVectors, byContent, true);

        List<ExactQuery> exactQueries = buildExactQueries(listings);
        List<float[]> exactVectors = embedding.embedBatch(exactQueries.stream().map(ExactQuery::text).toList(), 10);
        ExactResult exactVector = evaluateExact(store, exactQueries, exactVectors, byContent, false);
        ExactResult exactHybrid = evaluateExact(store, exactQueries, exactVectors, byContent, true);

        System.out.println("RAG_EVAL corpus=" + listings.size() + " cities="
                + listings.stream().map(Listing::city).distinct().count());
        System.out.println("RAG_EVAL constraint.vector " + vectorOnly.line());
        System.out.println("RAG_EVAL constraint.hybrid " + hybrid.line());
        System.out.println("RAG_EVAL exact.vector " + exactVector.line());
        System.out.println("RAG_EVAL exact.hybrid " + exactHybrid.line());
        store.close();
    }

    private Result evaluate(SQLiteVecStore store, List<Query> queries, List<float[]> vectors,
                            Map<String, Listing> byContent, boolean hybrid) {
        int city1 = 0, city3 = 0, city5 = 0, budget5 = 0, relevant = 0, retrieved = 0;
        double mrr = 0;
        long totalNanos = 0;
        for (int qi = 0; qi < queries.size(); qi++) {
            Query query = queries.get(qi);
            long start = System.nanoTime();
            List<VectorStore.SearchHit> hits = store.search("system", SQLiteVecStore.SHARED_KB_ID,
                    hybrid ? query.text() : null, vectors.get(qi), TOP_K, 1.5);
            totalNanos += System.nanoTime() - start;

            int firstCity = 0;
            int firstBudget = 0;
            for (int i = 0; i < hits.size(); i++) {
                retrieved++;
                Listing listing = byContent.get(hits.get(i).content());
                if (listing == null || !listing.city().equals(query.city())) {
                    continue;
                }
                if (firstCity == 0) {
                    firstCity = i + 1;
                }
                if (listing.price() <= query.budget()) {
                    relevant++;
                    if (firstBudget == 0) {
                        firstBudget = i + 1;
                    }
                }
            }
            if (firstCity == 1) city1++;
            if (firstCity > 0 && firstCity <= 3) city3++;
            if (firstCity > 0) city5++;
            if (firstBudget > 0) {
                budget5++;
                mrr += 1.0 / firstBudget;
            }
        }
        return new Result(queries.size(), city1, city3, city5, budget5, relevant, retrieved, mrr,
                totalNanos / Math.max(1, queries.size()) / 1000);
    }

    // 精确查询：城市 + 房源特征词（公寓/小区名），相关 = 同城且正文含该特征词
    private ExactResult evaluateExact(SQLiteVecStore store, List<ExactQuery> queries, List<float[]> vectors,
                                      Map<String, Listing> byContent, boolean hybrid) {
        int hit1 = 0, hit3 = 0, hit5 = 0, relevant = 0, retrieved = 0;
        double mrr = 0;
        long totalNanos = 0;
        for (int qi = 0; qi < queries.size(); qi++) {
            ExactQuery query = queries.get(qi);
            long start = System.nanoTime();
            List<VectorStore.SearchHit> hits = store.search("system", SQLiteVecStore.SHARED_KB_ID,
                    hybrid ? query.text() : null, vectors.get(qi), TOP_K, 1.5);
            totalNanos += System.nanoTime() - start;

            int firstRelevant = 0;
            for (int i = 0; i < hits.size(); i++) {
                retrieved++;
                Listing listing = byContent.get(hits.get(i).content());
                if (listing != null && listing.city().equals(query.city())
                        && listing.content().contains(query.token())) {
                    relevant++;
                    if (firstRelevant == 0) {
                        firstRelevant = i + 1;
                    }
                }
            }
            if (firstRelevant == 1) hit1++;
            if (firstRelevant > 0 && firstRelevant <= 3) hit3++;
            if (firstRelevant > 0) {
                hit5++;
                mrr += 1.0 / firstRelevant;
            }
        }
        return new ExactResult(queries.size(), hit1, hit3, hit5, relevant, retrieved, mrr,
                totalNanos / Math.max(1, queries.size()) / 1000);
    }

    private List<ExactQuery> buildExactQueries(List<Listing> listings) {
        List<ExactQuery> queries = new ArrayList<>();
        for (int i = 0; i < listings.size(); i += 4) {   // 抽样，控制 embedding 成本
            Listing listing = listings.get(i);
            String token = tokenOf(listing.content());
            if (token != null) {
                queries.add(new ExactQuery(listing.city(),
                        listing.city() + " " + token + " " + listing.price() + "元以内", token));
            }
        }
        return queries;
    }

    private String tokenOf(String content) {
        String[] parts = content.trim().split("\\s+");
        for (int i = 2; i < parts.length; i++) {
            String part = parts[i];
            if (part.length() >= 3 && !part.matches(".*\\d.*")
                    && !part.contains("区") && !part.contains("县") && !part.contains("元")) {
                return part;
            }
        }
        return null;
    }

    // 每个城市 3 条查询：城市 + 区 + 预算（25/50/75 分位），相关 = 同城且不超预算
    private List<Query> buildQueries(List<Listing> listings) {
        Map<String, List<Listing>> byCity = new TreeMap<>();
        for (Listing listing : listings) {
            byCity.computeIfAbsent(listing.city(), k -> new ArrayList<>()).add(listing);
        }
        List<Query> queries = new ArrayList<>();
        for (Map.Entry<String, List<Listing>> entry : byCity.entrySet()) {
            List<Listing> cityListings = entry.getValue();
            List<Integer> prices = cityListings.stream().map(Listing::price).sorted().toList();
            for (int pct : new int[]{25, 50, 75}) {
                int index = (int) Math.floor((prices.size() - 1) * pct / 100.0);
                int budget = prices.get(index);
                String district = districtOf(cityListings.get(0).content());
                queries.add(new Query(entry.getKey(),
                        entry.getKey() + " " + district + " " + budget + "元以内 一室", budget));
            }
        }
        return queries;
    }

    private String districtOf(String content) {
        String[] parts = content.trim().split("\\s+");
        for (int i = 1; i < Math.min(parts.length, 3); i++) {
            if (parts[i].length() >= 3 && !parts[i].matches(".*\\d.*")) {
                return parts[i];
            }
        }
        return "";
    }

    private List<Listing> load(Path dir) throws Exception {
        List<Listing> listings = new ArrayList<>();
        try (DirectoryStream<Path> stream = Files.newDirectoryStream(dir, "*.txt")) {
            for (Path file : stream) {
                String city = file.getFileName().toString().replaceFirst("\\.txt$", "");
                for (String line : Files.readAllLines(file, StandardCharsets.UTF_8)) {
                    String content = line.trim();
                    if (content.isEmpty()) {
                        continue;
                    }
                    Integer price = lastPrice(content);
                    if (price != null) {
                        listings.add(new Listing(city, content, price));
                    }
                }
            }
        }
        listings.sort(Comparator.comparing(Listing::city).thenComparing(Listing::content));
        return listings;
    }

    private Integer lastPrice(String content) {
        Matcher matcher = PRICE.matcher(content);
        Integer price = null;
        while (matcher.find()) {
            price = Integer.parseInt(matcher.group(1));
        }
        return price;
    }

    private Path findHousesDir() {
        Path p = Path.of("").toAbsolutePath();
        for (int i = 0; i < 6 && p != null; i++, p = p.getParent()) {
            Path candidate = p.resolve("agent/rag_data/houses");
            if (Files.isDirectory(candidate)) {
                return candidate;
            }
            Path direct = p.resolve("rag_data/houses");
            if (Files.isDirectory(direct)) {
                return direct;
            }
        }
        throw new IllegalStateException("找不到 agent/rag_data/houses");
    }
}
