package com.star.rag;

import java.nio.file.Files;
import java.nio.file.Path;

// 测试用：跨工作目录定位 vec0 原生扩展。
// Maven reactor 从模块根跑，IDEA 可能从仓库根跑，两种都要能找到。
public final class TestVecDll {

    private TestVecDll() {
    }

    public static String path() {
        Path p = Path.of("").toAbsolutePath();
        for (int i = 0; i < 5 && p != null; i++, p = p.getParent()) {
            for (String rel : new String[]{
                    "spike/sqlite-vec/vec0.dll", "spike/sqlite-vec/vec0.so",
                    "rag-mcp/vec0.dll", "rag-mcp/vec0.so",
                    "vec0.dll", "vec0.so"}) {
                Path candidate = p.resolve(rel);
                if (Files.exists(candidate)) {
                    return candidate.toString();
                }
            }
        }
        return "vec0.dll";
    }
}
