package com.star.agent.adapter;

import org.springframework.stereotype.Component;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.io.IOException;
import java.time.Duration;

// URL 图片下载器（HTTP 实现）：文生图/地图等 URL → 字节；失败抛异常由调用方降级
@Component
public class HttpImageFetcher implements ImageFetcher {

    private static final Duration TIMEOUT = Duration.ofSeconds(20);
    private final HttpClient http = HttpClient.newBuilder().connectTimeout(TIMEOUT).build();

    @Override
    public byte[] fetch(String url) throws Exception {
        HttpRequest req = HttpRequest.newBuilder(URI.create(url)).timeout(TIMEOUT).GET().build();
        HttpResponse<byte[]> resp = http.send(req, HttpResponse.BodyHandlers.ofByteArray());
        if (resp.statusCode() != 200) {
            throw new IOException("HTTP " + resp.statusCode());
        }
        return resp.body();
    }
}