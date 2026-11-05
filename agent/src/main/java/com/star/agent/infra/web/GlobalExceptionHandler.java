package com.star.agent.infra.web;

import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.MediaType;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.servlet.resource.NoResourceFoundException;
import org.springframework.web.HttpRequestMethodNotSupportedException;

// 全局异常处理：
//   BizException → 按其携带的 code/msg 返回（业务规则话术，如"用户名已被占用"）
//   调用方问题（405 方法不支持/400 缺参数/上传超限）→ 友好话术，不打堆栈（不是服务端故障）
//   静态资源不存在 → 抛回 Spring 默认 404（不能让 /xxx.html 404 变成 500 JSON）
//   其他异常 → 500 统一话术 + 服务端完整日志（不把堆栈泄露给前端）
// 响应体统一 {code,msg,data,traceId}（Result 工厂实时从 MDC 取，TraceIdFilter 已写入，前端可凭 traceId 查日志）
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger logger = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(BizException.class)
    public Result<Void> biz(BizException e) {
        return Result.fail(e.getCode(), e.getMessage());
    }

    @ExceptionHandler(NoResourceFoundException.class)
    public void noResource(NoResourceFoundException e) throws NoResourceFoundException {
        throw e;   // 交还 Spring 默认处理（404 页面/JSON），别被兜底 Exception 转成 500
    }

    // 请求方法不支持（如 POST 接口用 GET 调）→ 405，不是服务端故障（11-10 实测发现被兜成 500）
    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public Result<Void> methodNotSupported(HttpRequestMethodNotSupportedException e) {
        return Result.fail(405, "请求方式不支持（该接口支持 " + e.getSupportedHttpMethods() + "）");
    }

    // 缺少必填请求参数 → 400，调用方补参数即可
    @ExceptionHandler(MissingServletRequestParameterException.class)
    public Result<Void> missingParam(MissingServletRequestParameterException e) {
        return Result.fail(400, "缺少参数: " + e.getParameterName());
    }

    // 请求体缺失/格式错（@RequestBody 解析失败，如 POST 空 body）→ 400，不是服务端故障
    @ExceptionHandler(org.springframework.http.converter.HttpMessageNotReadableException.class)
    public Result<Void> badBody(org.springframework.http.converter.HttpMessageNotReadableException e) {
        return Result.fail(400, "请求体缺失或格式错误");
    }

    // @Valid 校验失败：只回第一个字段错误，话术直接可展示
    @ExceptionHandler(org.springframework.web.bind.MethodArgumentNotValidException.class)
    public Result<Void> invalidParam(org.springframework.web.bind.MethodArgumentNotValidException e) {
        String msg = e.getBindingResult().getFieldErrors().stream()
                .findFirst()
                .map(err -> err.getField() + " " + err.getDefaultMessage())
                .orElse("参数不合法");
        return Result.fail(400, msg);
    }

    // 上传超过 Tomcat multipart 上限（50MB）→ 友好话术，不是"服务器内部错误"
    @ExceptionHandler(MaxUploadSizeExceededException.class)
    public Result<Void> uploadTooLarge(MaxUploadSizeExceededException e) {
        return Result.fail(400, "文件过大（超过 50MB 限制）");
    }

    @ExceptionHandler(Exception.class)
    public Result<Void> other(Exception e, jakarta.servlet.http.HttpServletRequest request,
                              HttpServletResponse response) {
        String qs = request.getQueryString();
        logger.error("未处理异常: {} {}{}", request.getMethod(), request.getRequestURI(),
                qs != null ? "?" + qs : "", e);   // 完整日志栈（含 traceId，MDC 已写入）

        // SSE（text/event-stream）响应不能写 JSON：强行写会二次抛
        // HttpMessageNotWritableException，把一条普通异常放大成满屏堆栈。
        // 这类响应已在 ChatController 里以事件形式收尾，这里只记日志、不再写 body。
        if (response.isCommitted()) {
            return null;   // 响应已提交：任何写入都会二次抛，交回容器收尾
        }
        if (isEventStream(request, response)) {
            response.setStatus(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);   // SSE 只给状态码，不写 JSON
            return null;
        }
        return Result.fail(500, "服务器内部错误");
    }

    private boolean isEventStream(jakarta.servlet.http.HttpServletRequest request,
                                  HttpServletResponse response) {
        String contentType = response.getContentType();
        if (contentType != null && contentType.startsWith(MediaType.TEXT_EVENT_STREAM_VALUE)) {
            return true;
        }
        String accept = request.getHeader("Accept");
        return accept != null && accept.contains(MediaType.TEXT_EVENT_STREAM_VALUE);
    }
}