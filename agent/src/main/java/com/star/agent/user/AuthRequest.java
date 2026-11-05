package com.star.agent.user;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

// 用户认证接口（登录/注册页前端调用，契约 10-25 冻结）：
//   POST /api/user/register   {"type":"username",...} | {"type":"email",...}
//   POST /api/user/login      {"type":"username",...} | {"type":"email",...}
// 只校验“所有分支都必填”的 type；username/password/email/code 按 type 分支在 Service 里校验。
public record AuthRequest(
        @NotBlank(message = "不能为空") String type,
        String username,
        @Size(min = 6, max = 64, message = "长度需为 6~64") String password,
        @Email(message = "格式不正确") String email,
        @Size(min = 6, max = 6, message = "长度需为 6 位") String code) {
}
