package com.star.agent.media;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

// AudioTranscoder 单测：不依赖真实 ffmpeg——成功路径用假脚本模拟（复制输入当输出），
// 缺失路径传不存在的路径验证降级返回 null
class AudioTranscoderTest {

    @TempDir
    Path tmpDir;

    // 假 ffmpeg：把输入文件复制成输出文件（模拟"转码成功"）；参数位置固定同真实命令
    // 真实命令：ffmpeg -y -i <in> -ar 16000 -ac 1 <out>  → 输入是第 3 个参数，输出是第 8 个
    // Windows 用 .bat，Linux/macOS 用 .sh（CI 是 Ubuntu，不能执行 .bat）
    private Path fakeFfmpeg() throws Exception {
        if (isWindows()) {
            Path bat = tmpDir.resolve("fake-ffmpeg.bat");
            Files.writeString(bat, "@echo off\r\ncopy /y \"%~3\" \"%~8\" >nul\r\n");
            return bat;
        }
        Path sh = tmpDir.resolve("fake-ffmpeg.sh");
        Files.writeString(sh, "#!/bin/sh\ncp \"$3\" \"$8\"\n");
        assertTrue(sh.toFile().setExecutable(true), "假 ffmpeg 脚本应可执行");
        return sh;
    }

    private boolean isWindows() {
        return System.getProperty("os.name", "").toLowerCase().contains("win");
    }

    @Test
    void transcode_success_withFakeFfmpeg() throws Exception {
        AudioTranscoder transcoder = new AudioTranscoder(fakeFfmpeg().toString(), tmpDir);
        byte[] source = "fake voice bytes".getBytes(StandardCharsets.UTF_8);

        byte[] wav = transcoder.to16kWav(source);

        assertNotNull(wav, "假 ffmpeg 成功应返回字节");
        assertArrayEquals(source, wav, "假转码=原样复制");
    }

    @Test
    void transcode_missingFfmpeg_returnsNull() {
        AudioTranscoder transcoder = new AudioTranscoder(tmpDir.resolve("no-such-ffmpeg.exe").toString(), tmpDir);

        byte[] wav = transcoder.to16kWav(new byte[]{1, 2, 3});

        assertNull(wav, "ffmpeg 缺失应降级返回 null（R7）");
    }

    @Test
    void transcode_failingFfmpeg_returnsNull() throws Exception {
        // 假 ffmpeg 输出失败码 1：验证"转码失败"同样降级
        Path script;
        if (isWindows()) {
            script = tmpDir.resolve("fail-ffmpeg.bat");
            Files.writeString(script, "@echo off\r\nexit /b 1\r\n");
        } else {
            script = tmpDir.resolve("fail-ffmpeg.sh");
            Files.writeString(script, "#!/bin/sh\nexit 1\n");
            assertTrue(script.toFile().setExecutable(true), "假 ffmpeg 脚本应可执行");
        }
        AudioTranscoder transcoder = new AudioTranscoder(script.toString(), tmpDir);

        assertNull(transcoder.to16kWav(new byte[]{1, 2, 3}));
    }

    @Test
    void transcode_tempFilesCleaned() throws Exception {
        AudioTranscoder transcoder = new AudioTranscoder(fakeFfmpeg().toString(), tmpDir);
        transcoder.to16kWav("data".getBytes(StandardCharsets.UTF_8));

        try (var stream = Files.list(tmpDir)) {
            assertTrue(stream.noneMatch(p -> p.getFileName().toString().startsWith("voice-")),
                    "临时文件应清理干净");
        }
    }
}