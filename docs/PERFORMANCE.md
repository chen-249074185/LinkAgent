# 检索热路径压测

> 目标：验证混合检索（FTS5 + sqlite-vec + RRF）在单机 SQLite 上的吞吐与尾延迟。
> 环境：Windows、JDK 21、SQLite JDBC 3.45.3、内存库、单连接 + `synchronized`。

## 场景

| 项 | 值 |
|---|---:|
| 语料块数 | 5,000 |
| 查询数 | 2,000 |
| 向量维度 | 1,024 |
| topK | 5 |
| 并发 | 1 / 8 |

## 结果（本次运行）

| 并发 | QPS | p50 | p95 | p99 |
|---:|---:|---:|---:|---:|
| 1 | 105.7 | 9.00 ms | 12.11 ms | 13.89 ms |
| 8 | 105.3 | 9.76 ms | 423.30 ms | 657.09 ms |

## 分析

- 单线程下 105.7 QPS、p95 12 ms，满足单机个人助手场景。
- 8 并发下 QPS 仍是 105，p95 涨到 423 ms：`SQLiteVecStore` 的 `search()` 是 `synchronized`，所有读请求串行化，连接成为瓶颈。
- 这不是“SQLite 不行”，而是**单连接 + 串行读**的实现选择。当前项目的定位是单机部署，这个取舍是可接受的；多实例/高并发需要换实现。

## 优化方向

1. 读连接池 + WAL：`PRAGMA journal_mode=WAL`，读走独立连接，写走单连接。
2. 向量库换成 pgvector / Milvus：支持多实例、并发读。
3. 查询缓存：相同 query 的 embedding/检索结果缓存 5~10 分钟。
4. 把 `search()` 的 `synchronized` 收窄到写路径，读路径用连接池。

## 复现

```bash
RAG_BENCH=true mvn -pl rag-mcp -Dtest=HybridSearchBenchmarkTest test
```

测试会打印 `RAG_BENCH ...` 行。
