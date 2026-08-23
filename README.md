# Obsidian LLM Wiki Skill

用 LLM 持续维护 Obsidian 知识库的 Claude Code 全局 Skill。基于 raw/wiki/schema 三层架构，让 LLM 承担知识库的整理、交叉引用和更新工作。

## 灵感来源

本方案灵感来自 Andrej Karpathy 的 [llm-wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 知识管理理念。

Karpathy 的核心洞察：大多数人使用 LLM 处理文档的方式是 RAG —— 每次查询时从原始文档中检索片段、重新推导答案。这种方式没有知识积累。问一个需要综合五份文档的复杂问题，LLM 每次都要从头拼凑。

LLM Wiki 的做法不同：LLM **持续构建和维护一个持久化的 wiki** —— 一组结构化、互相链接的 markdown 文件，位于你和原始资料之间。每当你添加新资料，LLM 不会只为后续检索做索引，而是阅读、提取关键信息、整合到现有 wiki 中 —— 更新实体页面、修正主题摘要、标记新旧数据矛盾、强化或挑战正在形成的综合分析。知识编译一次，然后**保持最新**，而非每次查询重新推导。

> 维护知识库的枯燥部分不是阅读或思考 —— 而是簿记。更新交叉引用、保持摘要最新、标注矛盾、维护一致性。人类放弃 wiki 是因为维护负担增长快于价值。LLM 不会厌倦，不会忘记更新交叉引用，一次可以处理 15 个文件。

## 三层架构设计

```
┌─────────────────────────────────────────┐
│  Schema (CLAUDE.md)                     │  配置层：告诉 LLM 如何工作
│  领域注册表、命名约定、工作流、限制       │
├─────────────────────────────────────────┤
│  wiki/                                  │  可写层：LLM 生成和维护
│  摘要页面、实体页面、概念页面、综合分析   │
├─────────────────────────────────────────┤
│  raw/                                   │  不可变层：原始资料（只读）
│  PDF、网页剪藏、PPT、扫描件              │
└─────────────────────────────────────────┘
```

- **raw/** — 不可变原始资料。PDF、文章、网页剪藏、数据文件。LLM 只读取，绝不修改。这是事实来源。
- **wiki/** — LLM 生成的 markdown 文件。摘要、实体页面、概念页面、比较分析、综合报告。LLM 完全拥有这一层 —— 创建页面、更新页面、维护交叉引用、保持一致性。你阅读它，LLM 编写它。
- **Schema（`AGENTS.md` / `CLAUDE.md`，可双入口）** — 告诉 LLM wiki 的结构、约定、工作流的配置文件。推荐双入口：两份文件保存完全相同的内容，运行时只应用对应适配章节；结构变更时同步编辑两文件并验证 SHA-256。这是让 LLM 成为有纪律的 wiki 维护者而非通用聊天机器人的关键。你和 LLM 随着时间推移共同演化这个文件。

## Obsidian 集成

Obsidian 是这个方案的理想前端：

- **Obsidian 是 IDE，LLM 是程序员，wiki 是代码库。** LLM 在一侧编辑，你在另一侧实时浏览结果 —— 跟随链接、查看图谱视图、阅读更新后的页面。
- **Wiki 链接 `[[标题]]`** 实现页面间的自然关联，图谱视图直观展示知识网络。
- **YAML frontmatter** 让 Dataview 插件可以查询页面元数据，生成动态表格和列表。
- **Obsidian Web Clipper** 浏览器扩展可将网页快速转换为 markdown，直接进入 raw 收集。
- **附件管理** —— 图片等附件按领域分散在 raw/ 子目录中，与源资料同目录。

## 前置条件

- **Claude Code CLI** —— 已安装并配置（[安装指引](https://docs.anthropic.com/en/docs/claude-code)）
- **Obsidian** —— 本地已安装，vault 目录可被 Claude Code 访问
- **Schema（`AGENTS.md` 或 `CLAUDE.md`，推荐双入口）** —— 每个 Obsidian vault 根目录必须有 schema 文件。如果不存在，Skill 会引导你初始化。双入口时两文件字节一致并验 SHA-256

## 视觉 MCP 配置（可选）：智谱视觉理解 zai-mcp-server

第三方网关（如智谱 GLM）下 `Read` 图片可能仅返回 CDN 回执而无视觉内容（详见 SKILL.md「运行时与网关适配」）。配置智谱官方**视觉理解 MCP `zai-mcp-server`**（接入 GLM-4.6V，提供图像分析、OCR、技术图纸解读、图表阅读、视频理解等 8 个工具）后，即使网关多模态通道失效，Skill 仍可通过该 MCP 读图——`image_source` 支持本地绝对路径（含中文与空格路径）。

- 官方文档：<https://docs.bigmodel.cn/cn/coding-plan/mcp/vision-mcp-server>
- 前提：安装 [Node.js 18+](https://nodejs.org/en/download/)；从智谱[个人编程套餐](https://bigmodel.cn/coding-plan/personal/overview)或团队套餐（团队套餐 Key 与平台其他 API Key 不通用）获取 API Key

### 方式一：一键安装命令

把 `YOUR_API_KEY` 替换为你获取的 API Key：

```bash
claude mcp add -s user zai-mcp-server --env Z_AI_API_KEY=YOUR_API_KEY -- npx -y "@z_ai/mcp-server"
```

- 忘记替换 API Key 时，先 `claude mcp list` 确认、`claude mcp remove zai-mcp-server` 卸载旧条目，再重新执行安装命令。
- Windows PowerShell 下遇到 `-y` 参数问题时，改用命令提示符（CMD）执行同样命令；出现 `Windows requires 'cmd /c' wrapper to execute npx` 告警可以忽略。
- 旧缓存版本不含 GLM-4.6V 能力时，删除 npx 缓存，或改用 `@z_ai/mcp-server@latest` 强制安装最新版（≥ 0.1.2）。

### 方式二：手动配置 `~/.claude.json`

在用户目录下 `.claude.json` 顶层的 `mcpServers` 中追加（同样把 `YOUR_API_KEY` 替换为你的 API Key）：

```json
{
  "mcpServers": {
    "zai-mcp-server": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "-y",
        "@z_ai/mcp-server"
      ],
      "env": {
        "Z_AI_API_KEY": "YOUR_API_KEY",
        "Z_AI_MODE": "ZHIPU"
      }
    }
  }
}
```

环境变量：`Z_AI_API_KEY`（必需，智谱 API Key）、`Z_AI_MODE`（服务平台，`ZHIPU` 或 `ZAI`，默认 `ZHIPU`）。Windows 下 Claude Code 可能自动把 `command` 改写为 `cmd /c npx ...` 形式，属正常行为。配置后重启 Claude Code 生效。

### 使用注意

- **最佳实践**是把图片放在本地目录、在对话中用文件名或路径引用（如"分析 raw/xx/图1.png"）；直接在客户端粘贴图片不会走此 MCP。
- 该 MCP 是云端通道，图片内容会上送智谱服务器处理；敏感资料请自行评估是否走此通道。
- 在 Claude Code 中使用 GLM Coding Plan 时，模型服务端已内置 `image_analysis` 工具（仅支持远程 URL）；要获得本地路径读图与全部 8 个工具，仍需安装此 MCP。

## 限制条件

- 绝不修改 `raw/` 下的文件（不可变层）
- 覆盖已有 wiki 内容前须用户确认
- 编辑 wiki 页面时绝不删除已有图片引用（`![[...]]`），编辑前后校验图片引用完整性
- `log.md` 条目 append-only，不删除已有条目
- 保持中文为主要内容语言
- 不破坏已有 wiki 链接
- 所有路径和领域从项目 schema（`AGENTS.md` / `CLAUDE.md`）读取，不硬编码
- 双入口 schema 字节一致：结构变更同步两文件并验 SHA-256
- 不虚构来源、数据、引用或验证结果
- 中文路径与带空格路径用 `-LiteralPath` 或显式参数，不走 PowerShell 管道

## 文件结构

### obsidian-llm-wiki Skill 目录

```
~/.claude/skills/obsidian-llm-wiki/
├── SKILL.md              # Skill 主文件：命令定义、工作流、守则
├── README.md             # 本文件
├── assets/               # 通用页面模板
│   ├── wiki-page.md      # 通用 wiki 页面
│   ├── book-note.md      # 读书笔记
│   ├── meeting-note.md   # 会议记录
│   ├── tool-page.md      # 工具页面
│   └── log-active.md     # 新活动日志模板（仅在一次成功分卷轮转后使用）
├── scripts/
│   └── log-preflight.ps1 # 固定只读日志预检（2 MiB 阈值 + 跨年判定；Git Bash 经 powershell.exe 调用，中文文本走 -PendingAppendB64）
└── references/
    ├── schema.md         # AGENTS.md / CLAUDE.md 通用模板（供新项目初始化）
    ├── index_stat.py     # index.md 六变量精校脚本
    └── log-rotation.md   # 日志分卷/轮转参考（log status / query / rotate）
```

### Obsidian 仓库结构

```
<你的 vault>/
├── CLAUDE.md             # 模式配置（schema 层）
├── index.md              # 内容目录（LLM 维护）
├── log.md                # 操作日志（append-only）
├── raw/                  # 不可变原始资料
│   ├── <领域1>/          # 如 AI/、读书笔记/
│   │   ├── 技术文件/     # PDF、参考资料
│   │   └── ...
│   └── <领域2>/
└── wiki/                 # LLM 维护的 wiki
    ├── <领域1>/
    │   ├── 概览/
    │   ├── 工具/
    │   └── ...
    └── <领域2>/
```

## 命令一览

通过 `/obsidian-llm-wiki` 调用，支持以下子命令：

| 命令 | 说明 |
|---|---|
| `/obsidian-llm-wiki ingest <来源>` | 处理 raw/ 中的新资料，集成到 wiki。可能更新 10-15 个相关页面 |
| `/obsidian-llm-wiki query <问题>` | 使用 wiki 回答问题，综合多个页面并引用来源 |
| `/obsidian-llm-wiki lint` | 健康检查：矛盾、孤立页面、缺失引用、过期内容；同时校验 `index.md` 顶部维护块、底部三变量统计行与索引健康行的同步契约（六变量精校用 Skill 自带 `references/index_stat.py` + 双入口 schema 字节一致） |
| `/obsidian-llm-wiki migrate` | 一次性迁移：将已有笔记迁移到 LLM Wiki 模式 |
| `/obsidian-llm-wiki index` | 从当前 wiki 状态**全量重建** `index.md`，按三权威变量 + 三健康变量 + 索引健康行刷新。增量更新由 ingest/optimize/extract-thinking-frameworks/migrate/delete 触发；本命令只做全量重建。详见 SKILL.md `## Index Metadata And Statistics` |
| `/obsidian-llm-wiki log <mode>` | 日志工作流：`status`（只读预检详情）/ `query "<条件>"`（活动日志与历史分卷有界检索）/ `rotate now\|year\|size\|auto`（整文件移动式分卷轮转，见 `references/log-rotation.md`）。写入型任务追加 `log.md` 前自动跑 2 MiB 固定预检 |

## 日志预检与分卷（log）

`log.md` 是 append-only 操作日志，随维护持续增长（实测单 vault 可达数百 KB，超过 `Read` 工具上限）。本 Skill 为它提供「固定预检 → 安全追加 → 完整性验证 → 按需分卷」的完整治理机制：

### 追加前固定预检

写入型任务（ingest / optimize / migrate / index / 删除、归档、改名 / 实施修复的 lint）在追加最终日志条目前，构造完整待追加文本（含分隔换行与末尾换行），调用固定只读脚本 `scripts/log-preflight.ps1`（默认阈值 2 MiB；投影超阈值或活动日志跨年 → `rotation_due=true`）：

```bash
# Git Bash / Claude Code：多行中文文本走 Base64 通道，规避命令行换行/引号/编码风险
PENDING_B64=$(printf '%s' "$PENDING" | base64 -w0)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<skill>/scripts/log-preflight.ps1" \
  -VaultRoot "<vault>" -PendingAppendB64 "$PENDING_B64" -ThresholdMiB 2 -Json
```

原生 PowerShell（Codex / pwsh 会话）可直接传明文参数 `-PendingAppend "<完整待追加文本>"`，两条通道字节数完全等价。脚本只读：不创建/修改/移动/删除文件、不写临时文件、不输出日志正文；不得用临时生成的 Python/PowerShell/bash 代码替代。

### append-only 追加与验证

`rotation_due=false` 时用 heredoc 直追文件末尾（`cat >> log.md <<'LOGEOF'`，不整读大文件），追加前后做完整性验证：长度增量 == 待追加文本 UTF-8 字节数（预检的 `pending_bytes`）、任务标题在有界尾部恰好出现 1 次、文件仍以换行结束、`head -c <原长度> log.md | sha256sum` 前缀哈希 == 追加前整文件 SHA-256（证明既有字节零改动）。任一项不满足即如实报告，不宣称 append-only 成功。

### log 命令

| 命令 | 说明 |
|---|---|
| `log status` | 只读运行预检脚本 `-Detailed -Json`，展示当前/投影/阈值字节数与活动日志起始日期 |
| `log query "<条件>"` | 用 `rg` 检索活动日志与历史分卷，只读取命中处有界上下文 |
| `log rotate now` | 不问日期与大小，立即轮转 |
| `log rotate year` | 活动日志首条目早于当前日历年时轮转 |
| `log rotate size` | 投影字节数达到阈值时轮转 |
| `log rotate auto` | 年份或大小任一到期即轮转（写入任务的自动预检同此判定） |

### 分卷结构

```text
log.md                                          # 唯一活动日志
logs/log-archives.md                            # 分卷清单（首次真实轮转时创建）
logs/archive/log-YYYY-MM-DD-to-YYYY-MM-DD.md    # 历史分卷，永久只读
```

轮转采用**整文件移动**（绝不"复制后清空"、剪切条目或改写历史），移动前后校验字节长度、条目数与 SHA-256 完全一致；新活动日志从 `assets/log-active.md` 模板创建，不复制旧条目。`logs/` 不计入 `index.md` 页面统计。**轮转是组织行为，不是备份**——历史分卷永不自动删除、压缩或合并。完整流程见 [references/log-rotation.md](references/log-rotation.md)。

## SKILL.md 关键内容

SKILL.md 是 Skill 的核心配置，定义了：

1. **前置条件检查** —— 如果项目缺少 CLAUDE.md，引导用户初始化（询问领域 → 生成 CLAUDE.md → 创建目录结构）
2. **模板优先级** —— 项目 `templates/` 目录 > Skill `assets/` 目录。模板中 `{{domain}}`、`{{date}}` 等占位符由 Claude 根据项目 CLAUDE.md 填写
3. **页面规范** —— 每个 wiki 页面必须包含 YAML frontmatter（title、created、updated、domain、tags、sources、status）、inline tags、一句话摘要、正文、相关链接、来源引用
4. **工作流守则** —— raw/ 只读、覆盖前确认、日志 append-only、从 CLAUDE.md 读取配置而非硬编码
5. **index.md 同步契约** —— 顶部维护块、底部三变量统计行（`indexed_page_count` / `wiki_file_count` / `registered_domain_count`）与索引健康行（`missing_count` / `broken_count` / `duplicate_count`）的精确格式、六变量计数口径、强制维护遍历（Mandatory Maintenance Pass）与所有写命令的同步刷新策略（`## Index Metadata And Statistics`）
6. **运行时与网关适配** —— 读图前的视觉通道顺序探测（`Read` 单图 → 视觉理解 MCP 单图；智谱 GLM 等网关下 `Read` 图片可能仅返回 CDN 回执而无视觉内容，此时 `zai-mcp-server` 视觉 MCP 作为兜底通道，配置见上文「视觉 MCP 配置」）、两条通道都不可用时的 6 步降级（manifest 照建、视觉字段标"视觉未识别"、基于已有文字提炼、不虚构）、以及大 `log.md` 的追加前固定预检（`scripts/log-preflight.ps1`，2 MiB 阈值与跨年判定）与 EOF 直追（bash heredoc / `Add-Content -LiteralPath`，不为追加而整读；轮转见 `references/log-rotation.md`）。详见 SKILL.md `## 运行时与网关适配`

## 快速开始

### 1. 确认 Skill 可用

在任意目录下启动 Claude Code，输入 `/obsidian-llm-wiki`，确认 Skill 被识别。

### 2. 初始化新 Obsidian 仓库

在 Claude Code 中 `cd` 到你的 Obsidian vault 目录，运行 `/obsidian-llm-wiki`。如果缺少 CLAUDE.md，Skill 会引导你：

1. 告知你的知识库有哪些领域（如"读书笔记"、"AI"、"投资"）
2. 使用 `references/schema.md` 模板生成项目专属的 CLAUDE.md
   > Codex / 其他 agent 用户把文件名换成 `AGENTS.md` 即可，规则相同。
3. 创建 `raw/` 和 `wiki/` 目录结构
4. 创建空的 `index.md` 和 `log.md`

### 3. 开始使用

- 将原始资料放入 `raw/<领域>/` 对应目录
- 运行 `/obsidian-llm-wiki ingest` 处理新资料
- 运行 `/obsidian-llm-wiki query` 查询知识
- 定期运行 `/obsidian-llm-wiki lint` 保持 wiki 健康

### 4. Obsidian 设置

在 Obsidian 设置中，将 `Settings → Files & Links → Attachment folder path` 设为 `raw`，确保新图片附件暂存在 raw/ 根目录，ingest 时按领域整理到对应子目录。
