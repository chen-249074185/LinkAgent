# liepin-cli Skill（仓库 `skills/liepin-cli/`）

本目录由当前工程源码经 `liepin-cli skill install` **生成**，不要手改 `SKILL.md` 与 `reference.md`；安装说明与目标映射见本文件与 `install-targets.json`。

## 目录内容

- `SKILL.md`、`reference.md`：Agent 使用的技能正文
- `README.md`：本说明（人工安装与跨平台目标）
- `install-targets.json`：机器可读的平台安装路径映射

## 支持的安装目标

| Platform | Install root | What to copy | Notes |
|------|------|------|------|
| Cursor Project | `<project>/.cursor/skills` | `skills/liepin-cli` | Copy the liepin-cli folder from the repo into the project-level skills directory. |
| Cursor Home | `~/.cursor/skills` | `skills/liepin-cli` | Use this when you want the skill available across Cursor workspaces. |
| Claude Code | `~/.claude/skills` | `skills/liepin-cli` | Copy the liepin-cli folder into the Claude Code skills root. |
| Codex | `<codex-skill-root>` | `skills/liepin-cli` | Use the skills root configured by your Codex environment, then copy the liepin-cli folder into it. |
| OpenCode / OpenClaw-compatible | `<opencode-skill-root>` | `skills/liepin-cli` | Use the platform skill root, then copy the liepin-cli folder into it. |
| Cowork / Other Compatible Agents | `<platform-skill-root>` | `skills/liepin-cli` | Any agent platform that supports a skills directory can reuse the same liepin-cli folder. |

## 安装原则

1. 先确保目标环境已经可以运行 `liepin-cli`
2. 找到目标平台的 skills 根目录
3. 将本目录（`skills/liepin-cli/`）**整个**复制到该根下，使最终路径为 `<skills-root>/liepin-cli/`

## 目标说明

- 下列平台的默认安装路径已文档化：Cursor、Claude Code、Codex、OpenCode / OpenClaw-compatible
- `Cowork` 等未在当前仓库内建适配器的平台，同样复制本目录即可

## 重新生成 / 安装

在源码仓库根目录执行（推荐）：

```bash
uv run liepin-cli skill install
```

用户级 Cursor（`-g`）：

```bash
uv run liepin-cli skill install -g
```

默认会同时更新：
- `skills/liepin-cli/`（供 `npx skills add liubx009/liepin-cli` 等从仓库发现 Skill）
- `.cursor/skills/liepin-cli/`（本仓库内项目级 skill，便于开发）

## 说明

- `.cursor/skills/liepin-cli/` 在本仓库中视为同步产物，不应手工维护
- `install-targets.json` 提供机器可读的目标映射
