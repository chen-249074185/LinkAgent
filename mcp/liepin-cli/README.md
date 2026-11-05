# liepin-cli

[Python](https://www.python.org/downloads/)
[License](./pyproject.toml)

本地命令行工具，用于猎聘简历查询与更新、职位搜索与投递。适合人类用户与 AI Agent 在终端中协作使用。

[安装与快速开始](#安装与快速开始) · [安装 CLI SKILL](#安装-cli-skill必需) · [认证](#认证) · [命令与帮助](#命令与帮助) · [输出与校验](#输出模式) · [安全](#安全与风险提示)

## 为什么选 liepin-cli？

- **面向 Agent 友好** — 可导出 Cursor / Claude Code 等可用的 Skill，并支持 `--output json` 便于自动化解析
- **请求可校验** — 调用前按 JSON Schema 本地校验，减少无效请求
- **中文帮助** — 默认帮助优先展示业务参数，而非先罗列 token、base URL 等高级项
- **轻量依赖** — Typer、Pydantic、requests；Python 3.11+

## 功能


| 类别  | 能力                                       |
| --- | ---------------------------------------- |
| 简历  | 查询简历；更新基础资料、自我评价；维护教育 / 工作 / 项目经历；管理求职期望 |
| 职位  | 搜索职位；投递（`--job-kind` 须与搜索结果一致，勿凭感觉填写）    |


## 安装与快速开始

### 环境要求

开始之前，请确保具备：

- **Python** 3.11 或更高版本
- **包管理**：`pip`（随 Python 自带），或 **[uv](https://github.com/astral-sh/uv)**（本仓库含 `uv.lock`，便于与开发环境对齐）
- **Node.js**（`npm` / `npx`）— 仅在使用 `**npx skills add …`** 安装 Skill 时需要；若改用 `**uv run liepin-cli skill install**`（见下文），则不必安装 Node

### 快速开始（人类用户）

以下 **CLI 安装方式任选其一**；安装完成后请继续 **[安装 CLI SKILL（必需）](#安装-cli-skill必需)**。

#### 方式一 — pip + 虚拟环境（推荐）

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

安装完成后，优先使用控制台命令 `**liepin-cli**`；也可运行 `python -m liepin_cli.main`。

#### 方式二 — uv（与本仓库开发环境一致）

```bash
git clone https://github.com/liepin-tech-2026/liepin-cli.git
cd liepin-cli
uv sync
```

常用调用：`uv run liepin-cli --help`（或激活 `.venv` 后直接使用 `liepin-cli`）。

#### 方式三 — 从源码可编辑安装

```bash
git clone https://github.com/liepin-tech-2026/liepin-cli.git
cd liepin-cli
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### 安装 CLI SKILL（必需）

若你尚未安装 CLI，请先完成上文 **方式一 / 二 / 三** 之一，确保本机可执行 `liepin-cli`；Skill 只说明「何时、如何用 CLI」，不替代 CLI 本身。

**方式 A — `npx`（使用官方 `skills` 工具从 GitHub 安装，需 Node.js）**

```bash
npx skills add liepin-tech-2026/liepin-cli -y -g
```

**方式 B — `uv`（无需 Node，推荐在已克隆本仓库时使用）**

在仓库根目录执行（若当前目录不是克隆根目录，可加 `--repo-root /path/to/liepin-cli`）；`-g` 会**安装**到用户级 Cursor：`~/.cursor/skills/liepin-cli/`（语义接近上面的 `-g`），无需再手工复制。

```bash
uv run liepin-cli skill install -g
```

若只需要更新本仓库内的 skill 产物（`skills/`、`.cursor/skills/`），不写入用户主目录：

```bash
uv run liepin-cli skill install
```

更多平台与路径说明见 [Agent Skill 安装](#agent-skill-安装)。

### 配置与使用

1. **首次授权（仅需一次，需支持粘贴的交互式终端）**
  ```bash
   liepin-cli setup
  ```
   该流程会：尝试在浏览器中打开猎聘授权页（失败则提示手动访问 URL）、引导粘贴 `x-user-token`、写入本地配置，并用轻量接口校验 token。等效命令：`liepin-cli auth setup`。
2. **验证**
  ```bash
   liepin-cli resume get
  ```

### 快速开始（AI Agent）

> **Note for AI assistants：** 若你正在协助用户安装与授权，请按下列步骤执行；其中 **setup 必须由用户在可交互终端中完成**（本工具无法在非 TTY 环境粘贴 token）。

**第 1 步 — 安装 CLI**

指导用户在本地完成上文 [安装与快速开始](#安装与快速开始) 中「快速开始（人类用户）」的任一安装方式，确保 `liepin-cli` 在 `PATH` 中可用。

**第 2 步 — 授权**

请用户在终端执行 `liepin-cli setup` 或 `liepin-cli auth setup`。若 token 过期或失败：先 `liepin-cli auth open`，再 `liepin-cli auth setup`。

**第 3 步 — 验证**

```bash
liepin-cli resume get --output json
```

**第 4 步 — 安装 Agent Skill（与终端用户相同）**

有 Node 时优先：

```bash
npx skills add liepin-tech-2026/liepin-cli -y -g
```

无 Node 或用户已克隆本仓库时，在仓库根目录执行：

```bash
uv run liepin-cli skill install -g
```

详见 [Agent Skill 安装](#agent-skill-安装)。

---

## 认证

### Token 来源与优先级

CLI 按以下优先级解析 token：`**--token` > 环境变量 > 本地配置**（等价表述：--token > env > config）。

1. `**--token`**：命令行显式传入，优先级最高
2. `**LIEPIN_USER_TOKEN**`：环境变量
3. **本地配置文件**：`~/.config/liepin-cli/config.json`；若设置了 `XDG_CONFIG_HOME`，则为 `$XDG_CONFIG_HOME/liepin-cli/config.json`，字段名为 `token`

可先通过 `setup` 保存默认 token，再在单次调用中用 `--token` 临时覆盖。

### 授权子命令


| 子命令                      | 用途                            |
| ------------------------ | ----------------------------- |
| `liepin-cli auth setup`  | 交互式授权，与 `liepin-cli setup` 等价 |
| `liepin-cli auth status` | 查看已保存 token（脱敏）               |
| `liepin-cli auth clear`  | 清除本地已保存的 token                |
| `liepin-cli auth open`   | 打开猎聘授权页，便于刷新 token            |


非交互场景可仅使用环境变量：

```bash
export LIEPIN_USER_TOKEN="x-user-token-xxxxx"
liepin-cli resume get --token "$LIEPIN_USER_TOKEN"
```

## 命令与帮助

**命令分组**

- `liepin-cli setup`：首次配置或刷新登录状态
- `liepin-cli auth ...`：`setup`、`status`、`clear`、`open`
- `liepin-cli resume ...`：查询或更新简历
- `liepin-cli job ...`：搜索职位、投递职位
- `liepin-cli skill ...`：从本仓库生成 Agent Skill 并安装到本机（子命令 `install`，见 [安装 CLI SKILL](#安装-cli-skill必需)）

**查看 `--help`**

```bash
liepin-cli --help
liepin-cli auth --help
liepin-cli resume get --help
```

帮助优先展示业务相关命令与参数；骨架标题已中文化（如 `用法`、`选项`、`命令`、`参数`）。入门阅读顺序建议：

- `liepin-cli --help` → `setup`、`auth`、`resume`、`job`、`skill`
- `liepin-cli auth --help` → `status`、`clear`、`open`、`setup`
- `liepin-cli resume --help` → `get` 与各经历子命令
- `liepin-cli job --help` → `search`、`apply`
- `liepin-cli skill --help` → `install`（详见 [Agent Skill 安装](#agent-skill-安装)）

## Agent Skill 安装

若要让 Agent（Cursor、Claude Code、Codex 等）在合适场景下自动选用 `liepin-cli`，需要把 skill **安装**到各平台约定的 `skills` 目录。

### 推荐之一：`npx skills add`（需 Node.js）

```bash
npx skills add liepin-tech-2026/liepin-cli -y -g
```

仓库根目录提供 `skills/liepin-cli/`（含 `SKILL.md`、`reference.md`、`README.md`、`install-targets.json`），供 **skills** 工具从 GitHub 拉取。

### 推荐之二：`uv` + `liepin-cli skill install`（无需 Node，已克隆仓库时）

在**本仓库根目录**执行（不要手改 `.cursor/skills/liepin-cli/` 下的生成内容）：

```bash
uv run liepin-cli skill install
```

默认会同步更新：

- `skills/liepin-cli/`：与 `npx skills add` 约定一致的 **仓库根技能目录**（含生成后的安装说明与 `install-targets.json`）
- `.cursor/skills/liepin-cli/`：本仓库内 Cursor **项目级** skill（便于开发与自测；仅含 `SKILL.md` 与 `reference.md`）

**谁为主、如何保持一致**

- **唯一需要手改的来源**是仓库根目录 `README.md` 里的命令表（本节的 [命令总览](#命令总览) 与授权子命令表）。`liepin_cli/skill_distribution.py` 解析这些表生成 `SKILL.md` 与 `reference.md`。
- `**skills/liepin-cli/`** 下的技能正文与元数据 **全部由生成** 写入；**不要**直接编辑其中的 `SKILL.md`、`reference.md` 等，改表后在本仓库根执行 `uv run liepin-cli skill install` 再提交。
- 一致性由测试 `test_checked_in_generated_artifacts_match_current_bundle` 校验；`.cursor/skills/liepin-cli/` 仅在本机存在时参与校验（该路径默认不进 Git）。

**一键安装到本机用户目录**（无需 `cp`）：


| 目标                                         | 命令                                         |
| ------------------------------------------ | ------------------------------------------ |
| Cursor 用户级 `~/.cursor/skills/liepin-cli/`  | `uv run liepin-cli skill install -g`       |
| Claude Code `~/.claude/skills/liepin-cli/` | `uv run liepin-cli skill install --claude` |
| Codex 常见路径 `~/.agents/skills/liepin-cli/`  | `uv run liepin-cli skill install --codex`  |


可同时加多个标志（例如 `-g --claude`）。仅同步仓库内上述目录、不写入用户主目录时，使用 `uv run liepin-cli skill install` 且不加 `-g` / `--claude` / `--codex` 即可。

**仍需手工复制时**：把 `skills/liepin-cli/` **整个目录**复制到目标平台的 skills 根目录下，使最终路径为 `<skills-root>/liepin-cli/`。Cowork 等未单独列出的平台，只要支持 `skills/<name>/` 结构，同样复用该目录。

下面为**未使用 `skill install`**、仅从已生成目录复制时的参考命令；当前目录为**本仓库根目录**。

**Cursor（当前项目）**

```bash
mkdir -p .cursor/skills
cp -R skills/liepin-cli .cursor/skills/
```

**Cursor（用户目录，所有工作区可用）**

```bash
mkdir -p ~/.cursor/skills
cp -R skills/liepin-cli ~/.cursor/skills/
```

**Claude Code**

```bash
mkdir -p ~/.claude/skills
cp -R skills/liepin-cli ~/.claude/skills/
```

**Codex**（常见为 `~/.agents/skills`；若与你本机 Codex 配置不一致，以其文档或设置中的 skill 根目录为准）

```bash
mkdir -p ~/.agents/skills
cp -R skills/liepin-cli ~/.agents/skills/
```

**OpenCode / OpenClaw 等**：将同一 `liepin-cli` 文件夹复制到各工具说明中的 skill 根目录。

**Windows（PowerShell，在仓库根目录执行；路径按你的克隆位置调整）**——以 Cursor 项目级为例：

```powershell
New-Item -ItemType Directory -Force -Path .cursor\skills | Out-Null
Copy-Item -Recurse -Force skills\liepin-cli .cursor\skills\
```

Claude Code / Codex 的全局目录可分别改为 `$env:USERPROFILE\.claude\skills`、 `$env:USERPROFILE\.agents\skills`（若工具使用其它根目录，以其配置为准）。

机器可读的目标清单见 `skills/liepin-cli/install-targets.json`；更细的表格说明见 `skills/liepin-cli/README.md`。

**注意**：skill 只描述「何时、如何用 CLI」；使用前仍需在本机完成 [安装与快速开始](#安装与快速开始) 并完成授权（例如 `liepin-cli setup`）。

## 命令总览

### Resume 命令

| 命令                                     | 用途     | 常见关键参数                                                                             | 是否支持 `--input` |
| -------------------------------------- | ------ | ---------------------------------------------------------------------------------- | -------------- |
| `liepin-cli resume get`                | 获取当前简历 | 无                                                                                  | 否              |
| `liepin-cli resume update-base-info`   | 更新基础资料 | `--real-name`、`--sex`、`--birthday`、`--city-code`、`--start-job`、`--start-job-month` | 是              |
| `liepin-cli resume update-self-assess` | 更新自我评价 | `--self-assess`                                                                    | 是              |
| `liepin-cli resume add-edu-exp`        | 新增教育经历 | `--school`、`--major`、`--start`、`--end`、`--degree`                                  | 是              |
| `liepin-cli resume update-edu-exp`     | 更新教育经历 | `--edu-id`，以及学校/专业/起止时间/学历等字段                                                      | 是              |
| `liepin-cli resume add-work-exp`       | 新增工作经历 | `--comp-name`、`--rw-title`、`--work-start`、`--work-end`、`--salary`                  | 是              |
| `liepin-cli resume update-work-exp`    | 更新工作经历 | `--work-id`，以及公司/职位/时间/薪资等字段                                                       | 是              |
| `liepin-cli resume add-project-exp`    | 新增项目经历 | `--name`、`--start`、`--end`、`--position`                                            | 是              |
| `liepin-cli resume update-project-exp` | 更新项目经历 | `--id`，以及项目名称/时间/角色等字段                                                             | 是              |
| `liepin-cli resume add-job-want`       | 新增求职期望 | `--jobtitle`、`--dq`、`--want-salary-low`、`--want-salary-high`                       | 是              |
| `liepin-cli resume update-job-want`    | 更新求职期望 | `--id`，以及职位/地点/薪资等字段                                                               | 是              |


### Job 命令

| 命令                      | 用途   | 常见关键参数                                             | 是否支持 `--input` |
| ----------------------- | ---- | -------------------------------------------------- | -------------- |
| `liepin-cli job search` | 搜索职位 | `--job-name`、`--address`、`--salary-floor`、`--page` | 是              |
| `liepin-cli job apply`  | 投递职位 | `--job-id`、`--job-kind`（两者都必填）                     | 是              |


## 示例

```bash
liepin-cli resume get

liepin-cli job search --job-name "Python开发" --address "北京" --page 0

liepin-cli job apply --job-id 123456 --job-kind 2

liepin-cli resume update-base-info \
  --real-name "张三" \
  --sex 男 \
  --birthday 19950101

liepin-cli resume add-work-exp --input ./payloads/add-work-exp.json
```

其中：

- `job search --page 0` 通常表示第一页结果
- `job apply` 的 `--job-id` 和 `--job-kind` 都是必填
- `job apply` 的 `--job-kind` 需要传职位类型编号，例如 `1`、`2`；可以直接复用职位搜索结果里的“职位类型”值

## `--input` 与命令行参数的合并规则

如果同时传了 `--input` 和命令行参数：

1. 先读取 `--input` 指定的 JSON 文件
2. 再用显式传入的命令行参数覆盖同名字段
3. 在校验前移除未设置的空值

示例：

```bash
liepin-cli resume update-base-info \
  --input ./payloads/base-info.json \
  --city-code "上海"
```

## 参数名与 JSON 字段名的映射

CLI 参数名整体以现有接口定义为准，很多参数是 kebab-case，但并非所有字段都会转换成 camelCase；有些字段会直接沿用后端 schema 中的原始命名，例如 `--jobtitle`、`--dq`、`--workweek`、`--compkind`。

JSON payload 字段同样以 schema 原始定义为准，并不保证全部都是 camelCase。

常见映射示例：

- `--real-name` -> `realName`
- `--city-code` -> `cityCode`
- `--start-job` -> `startJob`
- `--start-job-month` -> `startJobMonth`
- `--now-work-status` -> `nowWorkStatus`
- `--comp-name` -> `compName`
- `--work-start` -> `workStart`
- `--work-end` -> `workEnd`
- `--want-salary-low` -> `wantSalaryLow`
- `--want-salary-high` -> `wantSalaryHigh`
- `--want-salary-months` -> `wantSalaryMonths`
- `--job-id` -> `jobId`
- `--job-kind` -> `jobKind`

数组字段可以通过重复传参来构造。例如：

```bash
liepin-cli resume add-job-want \
  --jobtitle "Java开发" \
  --dq "上海" \
  --industries "互联网" \
  --industries "金融"
```

会生成：

```json
{
  "jobtitle": "Java开发",
  "dq": "上海",
  "industries": ["互联网", "金融"]
}
```

## 示例 payload

下面展示的是一些常用命令对应的最小 `--input` 示例文件。

注意：下面出现的 `payloads/*.json` 路径只是示例，表示你需要在自己的工作目录里手动创建这些文件；它们不会随仓库一起提供，也不会随着 `liepin-cli` 安装自动生成。

`payloads/base-info.json`

```json
{
  "realName": "张三",
  "sex": "男",
  "birthday": "19950101",
  "startJob": "2020",
  "startJobMonth": "06"
}
```

`payloads/add-work-exp.json`

```json
{
  "compName": "猎聘",
  "rwTitle": "后端工程师",
  "workStart": "202301",
  "workEnd": "202402",
  "salary": 25000,
  "months": 14,
  "workType": 1
}
```

`payloads/add-job-want.json`

```json
{
  "jobtitle": "Java开发",
  "dq": "上海",
  "wantSalaryLow": 20000,
  "wantSalaryHigh": 30000,
  "wantSalaryMonths": 15,
  "workType": "0"
}
```

`payloads/search-job.json`

```json
{
  "jobName": "Python开发",
  "address": "北京",
  "page": 0
}
```

`payloads/apply-job.json`

```json
{
  "jobId": 123456,
  "jobKind": "2"
}
```

你可以这样调用：

```bash
liepin-cli resume update-base-info --input ./payloads/base-info.json
liepin-cli resume add-work-exp --input ./payloads/add-work-exp.json
liepin-cli resume add-job-want --input ./payloads/add-job-want.json
liepin-cli job search --input ./payloads/search-job.json
liepin-cli job apply --input ./payloads/apply-job.json
```

## 输出模式

- `--output pretty`：人类可读格式，默认值
- `--output json`：原样 JSON 输出到 stdout

对于字典或列表响应，`pretty` 和 `json` 当前都会输出格式化后的 JSON；两者主要区别体现在标量值和空响应上，例如 `pretty` 会把空响应显示为 `成功。`，而 `json` 会输出 `null`。

如果传入其它 `--output` 值，CLI 会在本地校验阶段直接报错，不会真正发请求。

## 本地校验

CLI 会在发起请求之前，先通过 Pydantic 对请求体做本地校验。无论输入来自 `--input` 文件还是命令行参数，都会经过这层校验。

当前已经包含的本地校验有：

- 不允许出现未知 JSON 字段
- 严格校验 `schemas/*.json` 中要求的必填字段
- 枚举型字段只能使用文档里允许的值
- 日期类字段会按文档要求校验格式，例如 `yyyyMMdd`、`YYYYMM`
- 对不能为负数的数值字段进行安全校验
- 校验 schema 中描述的跨字段规则，例如：
  - `startJob` 和 `startJobMonth` 必须同时出现
  - `wantSalaryLow` 不能大于 `wantSalaryHigh`

以下这类值会在本地直接被拒绝：

- `--output xml`
- `birthday=1990-01-01`
- `workStart=2023/01`
- `sex=未知`
- `page=-1`
- `wantSalaryLow=30000` 且 `wantSalaryHigh=20000`

## 退出码

- `0`：成功
- `1`：远端/API 失败，包括 HTTP 和网络传输错误
- `2`：本地输入或配置错误，例如缺少 token、JSON 非法、字段不合法、flag 值错误等

## 常见错误

- **缺少 token**：请确保 token 来自 `--token`、`LIEPIN_USER_TOKEN` 或本地配置文件（见[Token 来源与优先级](#token-来源与优先级)）。在交互终端里，CLI 会先在 **stderr** 打印 `未找到 token。请先运行 setup 流程。`，随后输出错误信息并退出。你可以运行 `liepin-cli setup` 或 `liepin-cli auth setup`，也可以手动设置环境变量或直接传 `--token`。
- **token 未授权或已失效**（HTTP 401/403）：请前往 [https://www.liepin.com/mcp/auth](https://www.liepin.com/mcp/auth) 重新获取 token。在交互终端里，CLI 会先在 **stderr** 打印 `授权失败。请尝试运行 liepin-cli setup 或 liepin-cli auth setup 刷新 token。`，随后输出接口错误信息并退出。如果你只想先打开授权页，可以先运行 `liepin-cli auth open`，再用 `liepin-cli auth setup` 保存并验证新 token。
- **JSON 输入非法**：请检查文件路径是否正确，以及 JSON 顶层结构是否符合对应命令要求（参考 `schemas/`）。
- `**--input` 中有未知字段**：请删除不在对应 schema 里的字段。
- **字段校验失败**：请修正枚举值、日期格式、数值范围或跨字段组合错误后重试。
- **输出模式非法**：`--output` 只能是 `pretty` 或 `json`。
- **HTTP 调用失败**：CLI 会输出状态码和接口返回内容，便于你定位远端错误。

## 安全与风险提示（使用前必读）

`liepin-cli` 与 AI Agent 结合使用时，存在误操作、提示词注入或过度授权等固有风险；token 代表你的猎聘账号能力范围，**切勿**将 token、配置文件或含 token 的日志提交到公开仓库或发给不可信第三方。

建议：仅在可信环境保存凭证；定期在猎聘侧轮换或刷新 token；对自动化脚本与 CI 使用最小权限与只读环境变量；向 Agent 暴露能力前确认其能访问的数据范围。使用本工具即表示你理解并接受上述风险。

## 贡献与许可证

欢迎通过 [Issue](https://github.com/liubx009/liepin-cli/issues) 或 Pull Request 反馈问题与改进建议。许可证与依赖说明以仓库内 `pyproject.toml` 及后续新增的 `LICENSE` 文件为准。
