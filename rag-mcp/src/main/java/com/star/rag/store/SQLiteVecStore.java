package com.star.rag.store;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.Set;
import java.util.UUID;

// VectorStore 的 sqlite-vec 实现（D37 方案 A）+ KnowledgeBaseRepository（user/知识库显式归属）
// 三块数据：vec_chunks 虚拟表（向量 KNN）+ chunks 普通表（正文/元数据）+ users/knowledge_base（归属管理）
// 共享房源库（11-03 用户拍板方案1）：房源=通用公开数据（爬链家），kb-shared-houses 全用户只读可检索，
// 归属 user_id=system；私有库（userId-default）仍是每用户私有
public class SQLiteVecStore implements VectorStore, KnowledgeBaseRepository {

    public static final String SHARED_KB_ID = "kb-shared-houses";   // 共享房源库（全局固定名）
    public static final String SHARED_OWNER = "system";             // 共享库的归属身份（数据由采集/管理端维护）

    private final Connection conn;

    // 打开数据库 + 加载 vec0 扩展 + 建表
    public SQLiteVecStore(String dbPath, String vecDllPath) throws Exception {
        Class.forName("org.sqlite.JDBC");          // 显式注册驱动（新版不自动 SPI）
        Properties props = new Properties();
        props.setProperty("enable_load_extension", "true");   // 允许 .load 外部扩展
        conn = DriverManager.getConnection("jdbc:sqlite:" + dbPath, props);

        // spike 已验证：Windows 上 vec0.dll 可正常加载
        try (Statement st = conn.createStatement()) {
            st.execute("SELECT load_extension('" + vecDllPath + "')");
        }
        initSchema();
    }

    // 建表：schema.sql 里的 DDL（幂等：IF NOT EXISTS）
    private void initSchema() throws Exception {
        try (Statement st = conn.createStatement()) {
            st.execute("CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(" +
                    "user_id TEXT partition key, kb_id TEXT, chunk_embedding float[1024])");
            st.execute("CREATE TABLE IF NOT EXISTS chunks (" +
                    "id INTEGER PRIMARY KEY AUTOINCREMENT," +
                    "kb_id TEXT NOT NULL, user_id TEXT NOT NULL," +
                    "content TEXT NOT NULL, embedding TEXT NOT NULL," +
                    "metadata_json TEXT," +
                    "created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')))");
            st.execute("CREATE INDEX IF NOT EXISTS idx_chunks_user ON chunks (user_id, kb_id)");
            // 分文件删除：chunks 加 filename 列——老库没有该列，幂等补列（PRAGMA 检查）
            if (!columnExists("chunks", "filename")) {
                st.execute("ALTER TABLE chunks ADD COLUMN filename TEXT");
                st.execute("CREATE INDEX IF NOT EXISTS idx_chunks_file ON chunks (user_id, kb_id, filename)");
            }
            // 关键词检索：FTS5 外部内容表（unicode61 对空格分词的房源语料更友好），触发器保持与 chunks 同步
            st.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(" +
                    "content, content='chunks', content_rowid='id', tokenize='unicode61')");
            st.execute("CREATE TRIGGER IF NOT EXISTS chunks_fts_ai AFTER INSERT ON chunks BEGIN " +
                    "INSERT INTO chunks_fts(rowid, content) VALUES (new.id, new.content); END");
            st.execute("CREATE TRIGGER IF NOT EXISTS chunks_fts_ad AFTER DELETE ON chunks BEGIN " +
                    "INSERT INTO chunks_fts(chunks_fts, rowid, content) VALUES('delete', old.id, old.content); END");
            st.execute("CREATE TRIGGER IF NOT EXISTS chunks_fts_au AFTER UPDATE ON chunks BEGIN " +
                    "INSERT INTO chunks_fts(chunks_fts, rowid, content) VALUES('delete', old.id, old.content); " +
                    "INSERT INTO chunks_fts(rowid, content) VALUES (new.id, new.content); END");
            // 第二套索引：trigram 处理无空格中文/子串（如"杭州市西湖区"），与 unicode61 互补
            st.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts_tri USING fts5(" +
                    "content, content='chunks', content_rowid='id', tokenize='trigram')");
            st.execute("CREATE TRIGGER IF NOT EXISTS chunks_fts_tri_ai AFTER INSERT ON chunks BEGIN " +
                    "INSERT INTO chunks_fts_tri(rowid, content) VALUES (new.id, new.content); END");
            st.execute("CREATE TRIGGER IF NOT EXISTS chunks_fts_tri_ad AFTER DELETE ON chunks BEGIN " +
                    "INSERT INTO chunks_fts_tri(chunks_fts_tri, rowid, content) VALUES('delete', old.id, old.content); END");
            st.execute("CREATE TRIGGER IF NOT EXISTS chunks_fts_tri_au AFTER UPDATE ON chunks BEGIN " +
                    "INSERT INTO chunks_fts_tri(chunks_fts_tri, rowid, content) VALUES('delete', old.id, old.content); " +
                    "INSERT INTO chunks_fts_tri(rowid, content) VALUES (new.id, new.content); END");
            // 老库首次加 FTS 时补建索引
            if (countRows("chunks_fts") == 0 && countRows("chunks") > 0) {
                st.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')");
            }
            if (countRows("chunks_fts_tri") == 0 && countRows("chunks") > 0) {
                st.execute("INSERT INTO chunks_fts_tri(chunks_fts_tri) VALUES('rebuild')");
            }
            // (09-29)：user 表 + knowledge_base 表，知识库归属显式化（R10）
            st.execute("CREATE TABLE IF NOT EXISTS users (" +
                    "user_id TEXT PRIMARY KEY," +
                    "created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')))");
            st.execute("CREATE TABLE IF NOT EXISTS knowledge_base (" +
                    "kb_id TEXT PRIMARY KEY," +
                    "user_id TEXT NOT NULL," +
                    "name TEXT NOT NULL," +
                    "created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')))");
            // 共享房源库归属行（幂等）：房源是通用公开数据，system 名下，全用户只读可检索
            st.execute("INSERT OR IGNORE INTO knowledge_base (kb_id, user_id, name) " +
                    "VALUES ('" + SHARED_KB_ID + "', '" + SHARED_OWNER + "', '共享房源库')");
            // 地址→经纬度缓存（地理编码结果，避免每次通勤测算都调高德 geocode）
            st.execute("CREATE TABLE IF NOT EXISTS geo_cache (" +
                    "address TEXT PRIMARY KEY," +
                    "location TEXT NOT NULL," +
                    "created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')))");
        }
    }

    // 存切片：正文/向量进 chunks 表，向量进 vec_chunks 虚拟表（rowid 对应）；返回新行号（回滚追踪用）
    // synchronized：单连接（conn）被灌入线程与工具调用并发使用，JDBC 连接非线程安全（R13 教训）
    @Override
    public synchronized int insertChunk(String userId, String kbId, String content, String filename, float[] embedding, String metadataJson) {
        try {
            String vecJson = toJson(embedding);
            // 先插普通表拿自增 id（rowid 就是 vec 表的 rowid）
            PreparedStatement ps = conn.prepareStatement(
                    "INSERT INTO chunks (kb_id, user_id, content, filename, embedding, metadata_json) VALUES (?,?,?,?,?,?)");
            ps.setString(1, kbId);
            ps.setString(2, userId);
            ps.setString(3, content);
            ps.setString(4, filename);
            ps.setString(5, vecJson);
            ps.setString(6, metadataJson);
            ps.executeUpdate();
            int rowId = ps.getGeneratedKeys().getInt(1);
            ps.close();

            // 再插虚拟表：user_id 作 partition key + 向量 JSON
            PreparedStatement vps = conn.prepareStatement(
                    "INSERT INTO vec_chunks (rowid, user_id, kb_id, chunk_embedding) VALUES (?,?,?,?)");
            vps.setInt(1, rowId);
            vps.setString(2, userId);
            vps.setString(3, kbId);
            vps.setString(4, vecJson);
            vps.executeUpdate();
            vps.close();
            return rowId;
        } catch (Exception e) {
            throw new RuntimeException("插入切片失败: " + e.getMessage(), e);
        }
    }

    // 按行号批量删切片（上传失败回滚）：正文表按 id、向量表按 rowid，两个表都要删
    @Override
    public synchronized void deleteChunks(String userId, List<Integer> rowIds) {
        if (rowIds == null || rowIds.isEmpty()) {
            return;                                     // 没入库过任何块 → 无事可回滚
        }
        String placeholders = String.join(",", java.util.Collections.nCopies(rowIds.size(), "?"));
        try {
            PreparedStatement vps = conn.prepareStatement(
                    "DELETE FROM vec_chunks WHERE rowid IN (" + placeholders + ")");
            for (int i = 0; i < rowIds.size(); i++) {
                vps.setInt(i + 1, rowIds.get(i));
            }
            vps.executeUpdate();
            vps.close();

            PreparedStatement ps = conn.prepareStatement(
                    "DELETE FROM chunks WHERE id IN (" + placeholders + ")");
            for (int i = 0; i < rowIds.size(); i++) {
                ps.setInt(i + 1, rowIds.get(i));
            }
            ps.executeUpdate();
            ps.close();
        } catch (Exception e) {
            throw new RuntimeException("回滚删除切片失败: " + e.getMessage(), e);
        }
    }

    // KNN 检索：MATCH 查询 + user_id/kb_id 过滤（partition key 自动只扫本区）
    // 注意：vec0 要求 KNN 查询必须带 k 约束（不能用参数化 LIMIT，坑：静态解析失败报
    // "A LIMIT or 'k = ?' constraint is required on vec0 knn queries"）
    // 去重（10-10 修复）：同一文档重复上传产生内容/向量完全相同的重复块，KNN 前 topK
    // 可能全是同一内容 → 多取几倍候选（fetchK 上限 100），按内容去重保留最低距离，
    // 再截断回 topK（KNN 按距离升序返回，首次见到的内容即最低距离那条）
    @Override
    public synchronized List<SearchHit> search(String userId, String kbId, float[] queryEmbedding, int topK, double threshold) {
        return search(userId, kbId, null, queryEmbedding, topK, threshold);
    }

    // 混合检索：向量候选 + FTS5 关键词候选，用 RRF 融合。
    // queryText 为空时退化为纯向量，保持旧调用/测试行为不变。
    @Override
    public synchronized List<SearchHit> search(String userId, String kbId, String queryText,
                                               float[] queryEmbedding, int topK, double threshold) {
        String owner = resolveOwner(userId, kbId);   // 共享库 → system 身份查（partition key 对齐）
        List<SearchHit> vectorHits = vectorSearch(owner, kbId, queryEmbedding, topK, threshold);
        if (queryText == null || queryText.isBlank()) {
            return vectorHits;
        }
        List<SearchHit> keywordHits = keywordSearch(owner, kbId, queryText, topK);
        return fuse(vectorHits, keywordHits, topK);
    }

    // KNN 向量检索（原逻辑）：阈值过滤 + 内容去重 + 截断 topK
    private List<SearchHit> vectorSearch(String owner, String kbId, float[] queryEmbedding,
                                         int topK, double threshold) {
        int fetchK = Math.min(Math.max(topK * 3, topK), 100);
        List<SearchHit> hits = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        try {
            String sql = "SELECT c.content, v.distance FROM vec_chunks v " +
                    "JOIN chunks c ON c.id = v.rowid " +
                    "WHERE v.chunk_embedding MATCH ? AND v.user_id = ? AND v.kb_id = ? " +
                    "AND k = ?";
            PreparedStatement ps = conn.prepareStatement(sql);
            ps.setString(1, toJson(queryEmbedding));
            ps.setString(2, owner);
            ps.setString(3, kbId);
            ps.setInt(4, fetchK);
            ResultSet rs = ps.executeQuery();
            while (rs.next()) {
                double score = rs.getDouble("distance");
                String content = rs.getString("content");
                if (score <= threshold && seen.add(content)) {   // 阈值过滤 + 内容去重
                    hits.add(new SearchHit(content, score));
                }
            }
            rs.close();
            ps.close();
        } catch (Exception e) {
            throw new RuntimeException("检索失败: " + e.getMessage(), e);
        }
        return hits.size() > topK ? hits.subList(0, topK) : hits;
    }

    // FTS5 关键词检索：unicode61（空格分词）+ trigram（无空格中文/子串）双索引，按排名融合
    private List<SearchHit> keywordSearch(String owner, String kbId, String queryText, int topK) {
        String ftsQuery = toFtsQuery(queryText);
        if (ftsQuery == null) {
            return List.of();
        }
        Map<String, Double> scores = new LinkedHashMap<>();
        searchFts("chunks_fts", ftsQuery, owner, kbId, topK, scores);
        if (scores.isEmpty()) {
            // 空格分词没命中（如"杭州市西湖区"连写）→ 用 trigram 子串索引兜底；
            // 只保留中文 token，避免预算数字（3000元）把无关城市带进来
            String triQuery = toFtsTriQuery(queryText);
            if (triQuery != null) {
                searchFts("chunks_fts_tri", triQuery, owner, kbId, topK, scores);
            }
        }
        return scores.entrySet().stream()
                .sorted(Map.Entry.<String, Double>comparingByValue().reversed())
                .limit(topK)
                .map(e -> new SearchHit(e.getKey(), 1.0 / (1.0 + e.getValue())))
                .toList();
    }

    private void searchFts(String table, String ftsQuery, String owner, String kbId,
                           int topK, Map<String, Double> scores) {
        int fetchK = Math.min(Math.max(topK * 3, topK), 100);
        try {
            String sql = "SELECT c.content, bm25(" + table + ") AS rank " +
                    "FROM " + table + " f JOIN chunks c ON c.id = f.rowid " +
                    "WHERE " + table + " MATCH ? AND c.user_id = ? AND c.kb_id = ? " +
                    "ORDER BY rank LIMIT ?";
            PreparedStatement ps = conn.prepareStatement(sql);
            ps.setString(1, ftsQuery);
            ps.setString(2, owner);
            ps.setString(3, kbId);
            ps.setInt(4, fetchK);
            ResultSet rs = ps.executeQuery();
            int rank = 0;
            while (rs.next()) {
                String content = rs.getString("content");
                if (!scores.containsKey(content)) {   // 同一内容只保留最好名次，避免重复行抬高分数
                    scores.put(content, 1.0 / (60 + rank + 1));
                }
                rank++;
            }
            rs.close();
            ps.close();
        } catch (Exception ignored) {
            // 单个索引失败不影响另一个索引和向量检索
        }
    }

    // RRF 重排：以向量候选为召回集，关键词只做加分，不额外引入候选。
    // 这样既保留向量召回率，又避免关键词把无关城市的房源带进来。
    private List<SearchHit> fuse(List<SearchHit> vectorHits, List<SearchHit> keywordHits, int topK) {
        if (vectorHits.isEmpty()) {
            return keywordHits.size() > topK ? keywordHits.subList(0, topK) : keywordHits;
        }
        Map<String, Integer> keywordRank = new LinkedHashMap<>();
        for (int i = 0; i < keywordHits.size(); i++) {
            keywordRank.putIfAbsent(keywordHits.get(i).content(), i);
        }
        Map<String, Double> rrf = new LinkedHashMap<>();
        for (int i = 0; i < vectorHits.size(); i++) {
            String content = vectorHits.get(i).content();
            double score = 1.0 / (60 + i + 1);
            Integer kr = keywordRank.get(content);
            if (kr != null) {
                score += 1.0 / (60 + kr + 1);
            }
            rrf.put(content, score);
        }
        return rrf.entrySet().stream()
                .sorted(Map.Entry.<String, Double>comparingByValue().reversed())
                .limit(topK)
                .map(e -> new SearchHit(e.getKey(), 1.0 / (1.0 + e.getValue())))
                .toList();
    }

    // 用户查询 → FTS5 MATCH 表达式：按标点/空白切词，3 字以上做 OR 短语
    private String toFtsTriQuery(String text) {
        if (text == null) {
            return null;
        }
        java.util.LinkedHashSet<String> grams = new java.util.LinkedHashSet<>();
        for (String token : text.replaceAll("[\\p{P}\\s]+", " ").trim().split("\\s+")) {
            if (token.length() < 3 || token.contains("元") || !token.matches(".*[\\u4e00-\\u9fff].*")) {
                continue;
            }
            // trigram 索引按 3 字窗口匹配；整词做 phrase 会因空格断开，拆成 n-gram OR 更稳
            for (int i = 0; i + 3 <= token.length() && grams.size() < 20; i++) {
                grams.add(token.substring(i, i + 3));
            }
        }
        if (grams.isEmpty()) {
            return null;
        }
        StringBuilder sb = new StringBuilder();
        for (String gram : grams) {
            if (sb.length() > 0) {
                sb.append(" OR ");
            }
            sb.append('"').append(gram).append('"');
        }
        return sb.toString();
    }

    private String toFtsQuery(String text) {
        if (text == null) {
            return null;
        }
        String normalized = text.replaceAll("[\\p{P}\\s]+", " ").trim();
        if (normalized.isEmpty()) {
            return null;
        }
        StringBuilder sb = new StringBuilder();
        for (String token : normalized.split("\\s+")) {
            if (token.length() < 3) {
                continue;
            }
            if (sb.length() > 0) {
                sb.append(" OR ");
            }
            sb.append('"').append(token.replace("\"", "\"\"")).append('"');
        }
        if (sb.length() == 0 && normalized.length() >= 3) {
            sb.append('"').append(normalized.replace("\"", "\"\"")).append('"');
        }
        return sb.length() == 0 ? null : sb.toString();
    }

    @Override
    public synchronized int deleteByKb(String userId, String kbId) {
        String owner = resolveOwner(userId, kbId);
        try {
            // 先按 kb_id 找出该库的 rowid 列表，再删虚拟表（vec0 支持 DELETE WHERE）
            PreparedStatement ps = conn.prepareStatement(
                    "DELETE FROM vec_chunks WHERE user_id = ? AND kb_id = ?");
            ps.setString(1, owner);
            ps.setString(2, kbId);
            int vecDeleted = ps.executeUpdate();
            ps.close();
            PreparedStatement ps2 = conn.prepareStatement(
                    "DELETE FROM chunks WHERE user_id = ? AND kb_id = ?");
            ps2.setString(1, owner);
            ps2.setString(2, kbId);
            int deleted = ps2.executeUpdate();
            ps2.close();
            return Math.max(vecDeleted, deleted);
        } catch (Exception e) {
            throw new RuntimeException("删除知识库失败: " + e.getMessage(), e);
        }
    }

    // 列出库内文件：按 filename 分组（块数 + 最后入库时间），老数据 filename 为 null 归 "(未知文件)"
    @Override
    public synchronized List<FileInfo> listFiles(String userId, String kbId) {
        String owner = resolveOwner(userId, kbId);
        try (PreparedStatement ps = conn.prepareStatement(
                "SELECT filename, COUNT(*) AS cnt, MAX(created_at) AS last_at " +
                        "FROM chunks WHERE user_id = ? AND kb_id = ? " +
                        "GROUP BY filename ORDER BY last_at DESC")) {
            ps.setString(1, owner);
            ps.setString(2, kbId);
            List<FileInfo> list = new ArrayList<>();
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    String name = rs.getString("filename");
                    list.add(new FileInfo(
                            name == null ? "(未知文件)" : name,
                            rs.getInt("cnt"),
                            rs.getString("last_at")));
                }
            }
            return list;
        } catch (Exception e) {
            throw new RuntimeException("列出库内文件失败: " + e.getMessage(), e);
        }
    }

    // 按文件名删库内全部切片：先查该文件的 rowid 列表，再 vec/chunks 双删
    @Override
    public synchronized int deleteFile(String userId, String kbId, String filename) {
        String owner = resolveOwner(userId, kbId);
        try {
            List<Integer> rowIds = new ArrayList<>();
            try (PreparedStatement ps = conn.prepareStatement(
                    "SELECT id FROM chunks WHERE user_id = ? AND kb_id = ? AND filename = ?")) {
                ps.setString(1, owner);
                ps.setString(2, kbId);
                ps.setString(3, filename);
                try (ResultSet rs = ps.executeQuery()) {
                    while (rs.next()) {
                        rowIds.add(rs.getInt(1));
                    }
                }
            }
            deleteChunks(userId, rowIds);   // 复用双删逻辑（vec_chunks 按 rowid + chunks 按 id）
            return rowIds.size();
        } catch (Exception e) {
            throw new RuntimeException("删除文件失败: " + e.getMessage(), e);
        }
    }

    // 归属校验（R10 显式版）：knowledge_base 表里有 (kb_id, user_id) 行才算拥有
    @Override
    public synchronized boolean ownsKb(String userId, String kbId) {
        try (PreparedStatement ps = conn.prepareStatement(
                "SELECT EXISTS(SELECT 1 FROM knowledge_base WHERE kb_id = ? AND user_id = ?)")) {
            ps.setString(1, kbId);
            ps.setString(2, userId);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.getBoolean(1);
            }
        } catch (Exception e) {
            throw new RuntimeException("校验知识库归属失败: " + e.getMessage(), e);
        }
    }

    // ===== KnowledgeBaseRepository 实现=====

    // 新用户自动建默认库：INSERT OR IGNORE 幂等（已存在不报错），默认库 kb_id = userId + "-default"
    @Override
    public synchronized KnowledgeBase ensureUserWithDefaultKb(String userId) {
        try {
            try (PreparedStatement ps = conn.prepareStatement(
                    "INSERT OR IGNORE INTO users (user_id) VALUES (?)")) {
                ps.setString(1, userId);
                ps.executeUpdate();
            }
            String defaultKbId = userId + "-default";
            try (PreparedStatement ps = conn.prepareStatement(
                    "INSERT OR IGNORE INTO knowledge_base (kb_id, user_id, name) VALUES (?,?,?)")) {
                ps.setString(1, defaultKbId);
                ps.setString(2, userId);
                ps.setString(3, "默认知识库");
                ps.executeUpdate();
            }
            return new KnowledgeBase(defaultKbId, userId, "默认知识库");
        } catch (Exception e) {
            throw new RuntimeException("创建默认知识库失败: " + e.getMessage(), e);
        }
    }

    // 新建命名知识库：kb_id 用 UUID 短前缀（跨用户不撞名）
    @Override
    public synchronized KnowledgeBase createKb(String userId, String name) {
        try {
            String kbId = "kb-" + UUID.randomUUID().toString().substring(0, 8);
            try (PreparedStatement ps = conn.prepareStatement(
                    "INSERT INTO knowledge_base (kb_id, user_id, name) VALUES (?,?,?)")) {
                ps.setString(1, kbId);
                ps.setString(2, userId);
                ps.setString(3, name);
                ps.executeUpdate();
            }
            return new KnowledgeBase(kbId, userId, name);
        } catch (Exception e) {
            throw new RuntimeException("创建知识库失败: " + e.getMessage(), e);
        }
    }

    // 列出用户全部知识库（含默认库）
    @Override
    public synchronized List<KnowledgeBase> listByUser(String userId) {
        try (PreparedStatement ps = conn.prepareStatement(
                "SELECT kb_id, user_id, name FROM knowledge_base WHERE user_id = ? ORDER BY created_at")) {
            ps.setString(1, userId);
            List<KnowledgeBase> list = new ArrayList<>();
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    list.add(new KnowledgeBase(
                            rs.getString("kb_id"), rs.getString("user_id"), rs.getString("name")));
                }
            }
            return list;
        } catch (Exception e) {
            throw new RuntimeException("列出知识库失败: " + e.getMessage(), e);
        }
    }

    // 列出全部用户的知识库（管理端全库视角，不做归属过滤）
    @Override
    public synchronized List<KnowledgeBase> listAll() {
        try (PreparedStatement ps = conn.prepareStatement(
                "SELECT kb_id, user_id, name FROM knowledge_base ORDER BY user_id, created_at")) {
            List<KnowledgeBase> list = new ArrayList<>();
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    list.add(new KnowledgeBase(
                            rs.getString("kb_id"), rs.getString("user_id"), rs.getString("name")));
                }
            }
            return list;
        } catch (Exception e) {
            throw new RuntimeException("列出全部知识库失败: " + e.getMessage(), e);
        }
    }

    // 删库：先删库内全部切片，再删 knowledge_base 行（调用方已做归属校验）
    @Override
    public synchronized void deleteKb(String userId, String kbId) {
        try {
            deleteByKb(userId, kbId);
            try (PreparedStatement ps = conn.prepareStatement(
                    "DELETE FROM knowledge_base WHERE kb_id = ? AND user_id = ?")) {
                ps.setString(1, kbId);
                ps.setString(2, userId);
                ps.executeUpdate();
            }
        } catch (Exception e) {
            throw new RuntimeException("删除知识库失败: " + e.getMessage(), e);
        }
    }

    // 账号合并：from 的全部知识库并入 to——
    // 默认库内容并入 to 默认库（kb_id 冲突）；非默认库改归属保留 kb_id（全局唯一不撞名）
    // vec_chunks 是虚拟表分区列不可 UPDATE → 逐行 DELETE+INSERT（rowid 不变，embedding 从 chunks 表取回）
    @Override
    public synchronized void transferTo(String fromUserId, String toUserId) {
        try {
            String fromDefault = fromUserId + "-default";
            String toDefault = toUserId + "-default";
            ensureUserWithDefaultKb(toUserId);   // 合并目标必须有默认库

            // 1) 读 from 的全部行（id + 原 kb_id + embedding JSON，用于重建 vec 行）
            List<Long> rowIds = new ArrayList<>();
            List<String> newKbIds = new ArrayList<>();
            List<String> vecJsons = new ArrayList<>();
            try (PreparedStatement ps = conn.prepareStatement(
                    "SELECT id, kb_id, embedding FROM chunks WHERE user_id = ?")) {
                ps.setString(1, fromUserId);
                try (ResultSet rs = ps.executeQuery()) {
                    while (rs.next()) {
                        String oldKb = rs.getString("kb_id");
                        rowIds.add(rs.getLong("id"));
                        newKbIds.add(oldKb.equals(fromDefault) ? toDefault : oldKb);
                        vecJsons.add(rs.getString("embedding"));
                    }
                }
            }

            // 2) chunks 普通表直接 UPDATE：默认库内容并入 to 默认库，非默认库只改归属
            try (PreparedStatement ps = conn.prepareStatement(
                    "UPDATE chunks SET user_id = ?, kb_id = ? WHERE user_id = ? AND kb_id = ?")) {
                ps.setString(1, toUserId);
                ps.setString(2, toDefault);
                ps.setString(3, fromUserId);
                ps.setString(4, fromDefault);
                ps.executeUpdate();
            }
            try (PreparedStatement ps = conn.prepareStatement(
                    "UPDATE chunks SET user_id = ? WHERE user_id = ? AND kb_id <> ?")) {
                ps.setString(1, toUserId);
                ps.setString(2, fromUserId);
                ps.setString(3, fromDefault);
                ps.executeUpdate();
            }

            // 3) vec_chunks 虚拟表：分区列不可 UPDATE → 逐行 DELETE + INSERT（rowid 不变）
            for (int i = 0; i < rowIds.size(); i++) {
                try (PreparedStatement del = conn.prepareStatement("DELETE FROM vec_chunks WHERE rowid = ?")) {
                    del.setLong(1, rowIds.get(i));
                    del.executeUpdate();
                }
                try (PreparedStatement ins = conn.prepareStatement(
                        "INSERT INTO vec_chunks (rowid, user_id, kb_id, chunk_embedding) VALUES (?,?,?,?)")) {
                    ins.setLong(1, rowIds.get(i));
                    ins.setString(2, toUserId);
                    ins.setString(3, newKbIds.get(i));
                    ins.setString(4, vecJsons.get(i));
                    ins.executeUpdate();
                }
            }

            // 4) knowledge_base：from 默认库行删（内容已并入 to 默认库），非默认库行改归属
            try (PreparedStatement ps = conn.prepareStatement(
                    "DELETE FROM knowledge_base WHERE user_id = ? AND kb_id = ?")) {
                ps.setString(1, fromUserId);
                ps.setString(2, fromDefault);
                ps.executeUpdate();
            }
            try (PreparedStatement ps = conn.prepareStatement(
                    "UPDATE knowledge_base SET user_id = ? WHERE user_id = ? AND kb_id <> ?")) {
                ps.setString(1, toUserId);
                ps.setString(2, fromUserId);
                ps.setString(3, fromDefault);
                ps.executeUpdate();
            }
            // 5) users：from 身份清理（账号已并入）
            try (PreparedStatement ps = conn.prepareStatement("DELETE FROM users WHERE user_id = ?")) {
                ps.setString(1, fromUserId);
                ps.executeUpdate();
            }
        } catch (Exception e) {
            throw new RuntimeException("知识库迁移失败: " + e.getMessage(), e);
        }
    }

    // float[] → "[0.1, 0.2, ...]"（vec0 接受 JSON 数组字符串）
    private String toJson(float[] arr) {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < arr.length; i++) {
            if (i > 0) sb.append(", ");
            sb.append(arr[i]);
        }
        return sb.append("]").toString();
    }

    // 表行数（FTS 首次建索引判断用）
    private long countRows(String table) throws Exception {
        try (Statement st = conn.createStatement();
             ResultSet rs = st.executeQuery("SELECT COUNT(*) FROM " + table)) {
            return rs.next() ? rs.getLong(1) : 0;
        }
    }

    // 表里是否已有某列（老库升级幂等用：CREATE TABLE IF NOT EXISTS 不会给已有表加列）
    private boolean columnExists(String table, String column) throws Exception {
        try (PreparedStatement ps = conn.prepareStatement("PRAGMA table_info(" + table + ")")) {
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    if (column.equals(rs.getString("name"))) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    // 是否是共享房源库（全局只读库：所有用户可检索，归属 system）
    public static boolean isSharedKb(String kbId) {
        return SHARED_KB_ID.equals(kbId);
    }

    // 查询身份解析：共享库 → system（vec_chunks partition key 对齐）；私有库 → 调用者自己
    private String resolveOwner(String userId, String kbId) {
        return isSharedKb(kbId) ? SHARED_OWNER : userId;
    }

    // 地理编码缓存：查（address → location 或 null）
    public synchronized String getGeoCache(String address) {
        try (PreparedStatement ps = conn.prepareStatement(
                "SELECT location FROM geo_cache WHERE address = ?")) {
            ps.setString(1, address);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? rs.getString("location") : null;
            }
        } catch (Exception e) {
            throw new RuntimeException("读取地理编码缓存失败: " + e.getMessage(), e);
        }
    }

    // 地理编码缓存：写（地址已存在则覆盖）
    public synchronized void putGeoCache(String address, String location) {
        try (PreparedStatement ps = conn.prepareStatement(
                "INSERT OR REPLACE INTO geo_cache (address, location) VALUES (?,?)")) {
            ps.setString(1, address);
            ps.setString(2, location);
            ps.executeUpdate();
        } catch (Exception e) {
            throw new RuntimeException("写入地理编码缓存失败: " + e.getMessage(), e);
        }
    }

    public void close() throws Exception {
        if (conn != null) conn.close();
    }
}