# liepin-cli Reference

This file is generated from the current project source. Use it as the heavier companion to `SKILL.md`.

## Install Context
- The target user should already have `liepin-cli` available.
- If not installed, follow the repository root `README.md` install section (`pip install -e` / `liepin-cli` on PATH).
- The local project documents auth, help, command tables, payload formats, and examples in `README.md`.

## Core Commands
```bash
liepin-cli setup
liepin-cli auth setup
liepin-cli auth status
liepin-cli auth open
liepin-cli auth clear

liepin-cli resume get --output json
liepin-cli job search --job-name "Java开发" --address "北京" --page 0 --output json
liepin-cli job apply --job-id 123456 --job-kind 2 --output json
```

## User-Facing Help Rule
- First-pass help should show only business-facing commands and flags.
- Do not mention hidden/internal flags unless the user explicitly asks for raw/full help.
- `job apply` first-pass help should focus on `--job-id` and `--job-kind`.
- `resume --help` first-pass help should stay at purpose plus subcommand overview.

### Auth Commands

| Command | Description |
|------|------|
| `liepin-cli auth setup` | 交互式授权，与 `liepin-cli setup` 等价 |
| `liepin-cli auth status` | 查看已保存 token（脱敏） |
| `liepin-cli auth clear` | 清除本地已保存的 token |
| `liepin-cli auth open` | 打开猎聘授权页，便于刷新 token |

### Resume Commands

| Command | Description | Common args | Supports `--input` |
|------|------|------|------|
| `liepin-cli resume get` | 获取当前简历 | 无 | 否 |
| `liepin-cli resume update-base-info` | 更新基础资料 | `--real-name`、`--sex`、`--birthday`、`--city-code`、`--start-job`、`--start-job-month` | 是 |
| `liepin-cli resume update-self-assess` | 更新自我评价 | `--self-assess` | 是 |
| `liepin-cli resume add-edu-exp` | 新增教育经历 | `--school`、`--major`、`--start`、`--end`、`--degree` | 是 |
| `liepin-cli resume update-edu-exp` | 更新教育经历 | `--edu-id`，以及学校/专业/起止时间/学历等字段 | 是 |
| `liepin-cli resume add-work-exp` | 新增工作经历 | `--comp-name`、`--rw-title`、`--work-start`、`--work-end`、`--salary` | 是 |
| `liepin-cli resume update-work-exp` | 更新工作经历 | `--work-id`，以及公司/职位/时间/薪资等字段 | 是 |
| `liepin-cli resume add-project-exp` | 新增项目经历 | `--name`、`--start`、`--end`、`--position` | 是 |
| `liepin-cli resume update-project-exp` | 更新项目经历 | `--id`，以及项目名称/时间/角色等字段 | 是 |
| `liepin-cli resume add-job-want` | 新增求职期望 | `--jobtitle`、`--dq`、`--want-salary-low`、`--want-salary-high` | 是 |
| `liepin-cli resume update-job-want` | 更新求职期望 | `--id`，以及职位/地点/薪资等字段 | 是 |

### Job Commands

| Command | Description | Common args | Supports `--input` |
|------|------|------|------|
| `liepin-cli job search` | 搜索职位 | `--job-name`、`--address`、`--salary-floor`、`--page` | 是 |
| `liepin-cli job apply` | 投递职位 | `--job-id`、`--job-kind`（两者都必填） | 是 |


## Auth Recovery
- Missing token: run `liepin-cli setup` or `liepin-cli auth setup`
- Unauthorized token: run `liepin-cli auth open`, then refresh with `liepin-cli auth setup`
- Token priority: `--token` > `LIEPIN_USER_TOKEN` > local config file

## `jobKind` Rule
- `job apply --job-kind` must use the returned type code such as `1` or `2`
- Search first, then reuse the returned type value

## `--input` Rule
- Many add/update commands support `--input <json-file>`
- Merge order: file first, explicit CLI overrides second, then null stripping and validation
- README payload paths are illustrative only and are not bundled

## Output Mode Rule
- Prefer `--output json` when Chat needs machine-readable output
- `pretty` may print `成功。` for empty responses while `json` prints `null`

## Agent 人工验收清单（手动）
在技能正文或 CLI 行为变更后、或对外发布前，用下表各测一遍：**先不加载**本 skill 记录基线，再**加载** `liepin-cli` skill 复测；失败则改 `SKILL.md` / 本文件后重跑。

| # | 示例提示 | 期望行为 |
|---|----------|----------|
| 1 | 用一句话说明根命令能做什么，不要提 token 和高级参数 | 只提业务向分组；首答不出现 `--token`、`--output`、`--base-url` 等（除非用户要看完整帮助）。 |
| 2 | 帮我查简历并把结果给你解析 | 使用或建议使用 `resume get` 且带 `--output json`。 |
| 3 | token 过期了怎么办 | 引导 `auth open` 再 `auth setup`（或 `setup`），优先 CLI 而非手写 HTTP。 |
| 4 | 直接投递职位（未给 search 结果） | 要求先 search 或索要 `job-id` 与来自结果的 `job-kind`，不猜测 kind。 |
| 5 | README 里的示例 payload 文件在哪个路径 | 说明仅示例、默认不随仓库提供该文件；不假定路径存在。 |

可选加压：提示里加「越快越好」，或将 1 与 4 合并，观察是否跳过规则。
