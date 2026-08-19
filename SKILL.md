---
name: obsidian-llm-wiki
description: "LLM Wiki 模式：用 LLM 持续维护 Obsidian 知识库（raw/wiki 双层 + AGENTS.md/CLAUDE.md schema + index.md + log.md）。支持 ingest、query、optimize、extract-thinking-frameworks、lint、index、migrate、delete；强制维护遍历（Mandatory Maintenance Pass）自动检查并修复 frontmatter/index/schema 结构缺口；index.md 统一三权威变量（indexed_page_count/wiki_file_count/registered_domain_count）+ 三健康变量（missing_count/broken_count/duplicate_count）+ 索引健康行；双入口 schema 字节一致并验 SHA-256。支持用 Claude Code Agent 工具派发只读 subagent 以波次并行分析图片密集资料（截图课程、PPT、扫描件，支持 100–300 张多 Agents 并行读图），用项目 .venv 做 PDF/DOCX/PPTX/XLSX 预处理与 image manifest。触发词：wiki、知识库维护、ingest、preprocess、batch-analyze images、subagent、波次并行、manifest、venv、optimize、lint、index、索引健康、六变量统计、双入口 schema、补录、漂移修正、知识管理、Obsidian 笔记整理、读图降级、视觉通道探测、视觉 MCP、zai-mcp-server、GLM-4.6V、GLM/MiniMax 网关、log.md 大文件追加。"
---

# Obsidian LLM Wiki Skill

用 LLM 持续维护 Obsidian 知识库。基于 raw / wiki / schema 三层架构：`raw/` 不可变源资料（只读），`wiki/` LLM 维护的知识层（可写），`CLAUDE.md` / `AGENTS.md` 为 schema。LLM 是维护者，人类负责策划原始资料、提问、引导方向。

本 Skill 是**通用方法论层**：subagent 批量分析、image manifest、文档预处理运行时、强制维护遍历、安全规则等跨 vault 复用的机制都在这里。项目特定的配置（领域、raw 目录树、运行环境）由项目根的 `CLAUDE.md` / `AGENTS.md` 承载，本 Skill 不重复。

## Grounding（schema 优先级与读取顺序）

每次进入一个 vault，按优先级读取 schema，确立架构、领域、路径、规则：

1. **`CLAUDE.md` / `AGENTS.md`**（schema 入口）— 见下方三情形
2. **`index.md`** — 现有内容目录，了解已有页面
3. **`log.md`**（尾部）— 近期操作，了解最新变更

**schema 双入口三情形**（关键：按 vault 声明的契约处理两份 schema）：

1. **声明双入口字节契约**（两文件内容完全相同，典型如 Lester 知识库）：两份文件必须字节一致；结构变更时**同一次编辑同步两个文件**，并验证 SHA-256 相等；运行时只应用与当前运行时匹配的适配章节（Claude Code 侧用 Claude Code 适配章节）。这是项目契约，不是建议。
2. **未声明契约且两文件冲突**：Claude Code 侧以 `CLAUDE.md` 为准，并在结果中记录任务相关的冲突，提示用户裁定。
3. **仅存在一个 schema 文件**：直接使用之。本地默认与最常见即单个 `CLAUDE.md`（Claude Code 原生自动加载）；Codex 单文件通常是 `AGENTS.md`。

> 所有路径、领域、frontmatter 规范从 schema 读取，**不硬编码**。发现双入口契约下两文件不一致时，必须报告，不擅自改写。

## 强制维护遍历（Mandatory Maintenance Pass）

**每次使用本 Skill 都包含一次强制维护遍历**。用户无需显式要求"更新 index.md / 修复 frontmatter / 同步 schema"——自动检查并在发现结构缺口时修复。

**用户显式边界仍优先**：若用户声明只读 / 审计 / 查询 / "不改任何文件"，则执行同样的检查，但**只报告 gaps，不写入**。

在每次任务收尾前运行这七步：

1. 读 `AGENTS.md` / `CLAUDE.md`（在时）与 `index.md`。
2. 识别任务作用域内的 wiki 页面：ingest / optimize / migrate / delete / extract-thinking 任务 = 所有新建、修改、移动、删除或被直接引用为产出的页面；query 任务 = 为回答而读的页面；lint / audit / index 任务 = 用户指定作用域，未指定则全库。
3. 检查作用域页面的 YAML frontmatter 七字段（`title` / `created` / `updated` / `domain` / `tags` / `sources` / `status`）。frontmatter 是**结构性维护例外**：缺失或错位时默认修复到文件第一行，**不受** "append-only / 保留正文 / 放最后" 约束（这些约束只针对正文、图片与章节顺序）。只有显式 "不改任何文件" 才不写。缺失值按文件名 / schema 路径 / 今日 / 声明 sources / 当前页面状态保守推断；`domain` 或 `source` 推断不确定才问用户。
4. 检查 `index.md` 任务作用域相关条目（新增 / 移除 / 迁移 / 改名 / 缺条 / 路径过期 / 摘要过期 / 标签变化 / 统计漂移 / 重复 / 断链）。改 `index.md` 前先扫 `wiki/**/*.md` + 读现有 index + 按 §Index Metadata And Statistics 重算六个变量；改 index 时**同一次编辑**刷新顶部维护说明 + 底部统计行 + 索引健康行。
5. 检查 `AGENTS.md` / `CLAUDE.md` 中与任务相关的领域注册、raw/wiki 路径、工作流、安全、标签、图片/文档规则是否过期；按 vault 双入口契约处理（同步两文件 + 验 SHA-256）。
6. 若有文件变更，向 `log.md` 追加**一条**最终记录，含 `AGENTS.md` / `CLAUDE.md` / `index.md` / frontmatter 四项检查结果（含 "已检查，无需更新"）；若 `index.md` 变更，记录三个权威变量 + 三个健康计数 + `indexed_page_count` 变化类型（变化 / 不变 / 统计漂移修正）。无维护变更但其他文件变更时，仍为每个检查项记 `已检查，无需更新`。（`log.md` 变大时按 §运行时与网关适配 的 EOF 直追法追加，勿整读。）
7. 维护遍历**只动结构与元数据**：不因发现元数据或索引缺口就扩写、改写或重新诠释源资料正文。

> 本节取代旧版"Schema 与 Index 新鲜度检查"章节——那节的"只读默认不改、写操作必检查并记录"分工已并入本遍历。主 Claude agent 拥有此遍历与所有写入；subagent 只辅助分析。

## 安全规则

- **绝不修改、移动、删除 `raw/` 下任何文件**（不可变层）。
- **`log.md` 条目 append-only**，不删除、不改写已有条目，只追加。
- **覆盖已有 wiki 内容前须用户确认**；优化页面时**绝不删除已有的 `![[图片.png]]` 嵌入**。
- **删除 wiki 页面**用精确路径，禁通配符/递归/管道批量/循环/目录删除：

  ```powershell
  Remove-Item -LiteralPath "<绝对路径>"
  ```

  单文件单命令；中文路径与带空格路径必须用 `-LiteralPath` 或被正确引用的显式参数。
- **双入口 schema 字节一致性**：声明双入口契约时，`AGENTS.md` 与 `CLAUDE.md` 必须字节相同；结构变更**同步编辑两文件并验证 SHA-256**；不得泄露密钥或本地敏感配置。
- **subagent 只读红线**：派出的 subagent 绝不修改 `raw/`、`wiki/`、`index.md`、`log.md`、schema 文件或 `.claude/` 下任何文件。
- 不确定时**提问，不猜测**；图片重名/缺失/无法唯一定位一律先报告。
- **不虚构**来源、数据、引用或验证结果。
- 不修改 Windows 系统 PATH，不自动安装/卸载/重装 Python，不调用用户目录下的 Python；不通过 PowerShell 管道向 Python 传递中文路径。
- 图片嵌入用短文件名 `![[文件名.png]]`，不写完整路径（Obsidian 全库自动解析）。
- **图片视觉未识别时必须如实标注**（视觉未识别 / 基于正文非图像识别），绝不依文件名或上下文虚构图中文字、人物、数字、颜色。
- **`log.md` 大文件（超 `Read` 上限）追加用 EOF 直追**（bash heredoc / `Add-Content -LiteralPath`），不为追加而整读。

## 前置条件（初始化）

使用前，项目根目录必须有 schema 文件（本地默认与推荐：单个 `CLAUDE.md`，Claude Code 原生自动加载）。如果不存在，引导用户初始化：

1. 询问用户的知识库有哪些领域（如"读书笔记"、"AI"、"投资"）
2. 使用 [references/schema.md](references/schema.md) 作为模板，生成项目专属的 `CLAUDE.md`（Claude Code 原生自动加载，本地默认与首选）。若同一 vault 也用 Codex / 其他 agent，再把完全相同的内容另存为 `AGENTS.md`（双入口，处理见三情形 case 1）。
3. 创建 `raw/` 和 `wiki/` 目录结构
4. 创建空的 `index.md` 和 `log.md`
5. 在 Obsidian 设置中将 `attachmentFolderPath` 设为 `raw`（新图片暂存 raw/ 根目录，ingest 时按领域整理到对应子目录）

## 模板

本 Skill 自带通用模板，位于 `assets/` 目录：

- `assets/wiki-page.md` — 通用 wiki 页面
- `assets/book-note.md` — 读书笔记
- `assets/meeting-note.md` — 会议记录
- `assets/tool-page.md` — 工具页面

**优先级**：如果项目根目录有 `templates/` 目录，优先使用项目模板；否则使用 Skill 自带的 `assets/` 模板。模板中的 `{{domain}}`、`{{date}}`、`{{title}}` 等占位符由主 agent 根据项目 schema 填写。

## Frontmatter 与 Tag 规范化

每个 wiki 页面必须以 YAML frontmatter 开头（文件第一行，`---` 起始），必需七字段：

```yaml
---
title: "页面标题"
created: YYYY-MM-DD
updated: YYYY-MM-DD
domain: <领域名>
tags: [type/book, AI/编程]
sources: []
status: draft | active | archived
---
```

- `title` 与文件名一致；`sources` 指向 raw 来源目录（以 `/` 结尾）或文件路径，多个用 YAML 数组；`updated` 在正文、标签或来源元数据实质变化时刷新。
- `tags` 是权威来源；inline `#tag` 如存在必须与 frontmatter 匹配。
- **Tag 规范化**：只在 frontmatter `tags` 与 inline `#tag` 中规范化，**不自动改** domain、sources、raw/wiki 路径、目录名、文件名、页面标题、wiki 链接、图片嵌入或正文普通文本。标签片段中如有空白，统一用 `_` 连接（如 `AI Live` → `AI_Live`）。
- **结构性维护例外**：frontmatter 缺失或错位时，即使用户说 "append-only / 不改现有内容 / 放最后"，仍默认把 frontmatter 修复到第一行——这不计入"改动正文或顺序"。只有显式 "只读 / 不改任何文件" 才阻止写入。

## Windows 与 Python

文档预处理优先用项目 Python 虚拟环境，**不依赖系统** `python` / `py` / `python3`。文件发现优先用 `rg`。解释器优先级链：

1. `.venv\Scripts\python.exe`（项目本地，首选）
2. `.claude-python\python.exe`（可选项目目录）
3. `.runtime\python\python.exe`（可选）

脚本必须用 `pathlib.Path` 处理路径（跨平台、Windows 中文路径友好）。**中文路径与内容必须作为 PowerShell 显式参数传递，不通过管道喂给 Python**。不修改 PATH、不安装/卸载/重装 Python、不调用户目录 Python。调用约定见下文「文档预处理运行时」。

## 文档预处理运行时（Document Preprocessing Runtime）

PDF/DOCX/PPTX/XLSX 等文档的确定性预处理，与只读 subagent 视觉分析分工协作。

**调用格式**（项目脚本就位后）：

```powershell
& ".\.venv\Scripts\python.exe" ".\scripts\<script>.py" "<input-path>" "<output-path>"
```

**`.venv` 职责**（确定性、可重复）：
- 从 DOCX / PDF / PPTX / XLSX 提取文本与元数据
- 提取或枚举内嵌图片、slide/page 顺序、文件名、尺寸、源文档引用
- 仅在用户明确要求生成新源资产时，才把 PDF 页面或 PPTX 幻灯片渲染为图片文件
- 为后续只读 subagent 视觉分析建立有序 manifest
- **中间产物默认不写入 `raw/`**，除非用户明确要求

**`.venv` 与 subagent 分工**：
- `.venv` 负责可重复的解析、排序、抽取、manifest 建立
- 只读 subagent 负责 OCR-like 图片阅读、截图理解、图表/UI 细节、概念洞见合成
- **不默认假设** Tesseract、OpenCV、PaddleOCR、RapidOCR 等传统 OCR 引擎可用，除非用户明确安装或要求

> 项目 `scripts/` 是否就位、依赖是否安装，以项目 schema（CLAUDE.md 的「运行环境」章节）为准；未就位时 PDF 用 Read 的 `pages` 参数直读降级。

## 图片密集资料分析（Image-Heavy Source Analysis）

适用范围：raw 图片目录、截图课程、PPT 截图导出、wiki 页面中以 `![[...]]` 引用 raw 图片的页面、以及从 PDF/DOCX/PPTX 中抽取出页面或图片的资料。

1. **先建 image manifest，再分析**：
   - 对 wiki 页面：按**文档顺序**提取每个 `![[...]]` 嵌入，解析短文件名时优先用页面 `sources` 声明的 raw 目录。
   - 对 raw-only 图片目录：按自然文件名顺序处理。
   - 对 PDF/DOCX/PPTX 源：先用 `.venv` 检查文本、内嵌媒体、page/slide 顺序与文档元数据，再决定如何把图片分配到批次。
   - 若 `sources` 为空或不完整：按精确文件名全库搜索，报告未解析或歧义匹配。
   - **视觉通道探测**：建 manifest 后、派发读图前，先按 §运行时与网关适配 做视觉通道顺序探测（`Read` 单图 → 视觉理解 MCP（如 zai-mcp-server）单图）；两条通道都不可用才走降级（manifest 照建，视觉字段标"视觉未识别"，基于已有文字提炼）。
2. **保留顺序**：已有 wiki 嵌入顺序是权威顺序；raw-only 图片集用自然文件名顺序；优化时不擅自重排嵌入，除非用户明确要求。
3. **覆盖风险检测（报告而不猜测）**：检测重名文件、缺失文件、非图片嵌入、位于 declared `sources` 之外的图片；**不要猜测**哪个重名图是意图所指——报告出来让用户/主 agent 决定。
4. **分析可追溯**：中间笔记放工作上下文或最终回复，**不写 `raw/`**；写 wiki 内容时用文件名 + manifest index 标识每张图。

## Subagent 批量分析（Claude Code 适配）

当用户明确要求 subagent / 并行 agent / 批量图片分析时，主 agent 用 Claude Code 的 **`Agent`（Task）工具**派发只读 subagent。

> 术语映射：Codex 侧现行接口是 `collaboration.spawn_agent(agent_type: "default")`；在 Claude Code 对应 `Agent` 工具调用，`subagent_type` 用项目自定义只读 subagent（如 `image-reader`）或内置 **`Explore`** 类型（同样只读）。两侧职责划分一致。

**主 agent 独占四件事**：manifest 建立、分批/分波、最终合成、所有写文件。subagent 只读图返回分析。

**分批与波次机制（支持 100–300 张大批量多 Agents 并行读图）**：

| 图片数 | 策略 |
|---|---|
| 1–10 | 主 agent 本地直接读取分析，除非委派更有利 |
| 11–30 | 拆成 2–3 个只读 subagent 批次 |
| 31+ | 拆成 ≤6 个只读 subagent 批次（单波并发上限 ≤6） |

**波次（waves）推进大批量**：
- **单批容量**：每个 subagent 单批控制在合理大小（默认每批 ≤30 张，沿用 11–30 档经验，避免单 subagent 上下文过载）。
- **单波并发**：每波同时派发 ≤6 个只读 subagent（单条消息内多个 `Agent` tool use 即并发）。Claude Code 动态 Workflow 理论并发上限为 16，但**第三方网关可用性未经验证**，保守取 ≤6。注意：网关并发与"读图视觉通道"是两个独立问题——某些网关下 `Read` 图片仅返回 CDN 上传回执而无视觉内容（见 §运行时与网关适配），需先做视觉通道顺序探测再决定读图方式：`Read` 可用则照常派发 Read 批次；`Read` 不可用但视觉 MCP 可用（见 §视觉理解 MCP 通道）时，subagent 已被授予视觉 MCP 工具则照常派发批次（subagent 用 MCP 工具替代 `Read` 读图），未授予则由主线程分批逐张调用 MCP 工具并按 manifest 对账。
- **多波推进**：当总量超过单波容量（如 100–300 张）时，以**波次**持续推进——主 agent 每波派发 ≤6 个 subagent 并行读图，每波返回后按 manifest 序号对账，再派发下一波，直到 manifest 全部图片处理完。波次数不限（300 张 ÷ 约 90 张/波 ≈ 2–4 波）。运行时并发低于批数时也以波次执行这同一批数目，**不增加批次总数、不削弱大批量能力**。

> 这是对旧版"100+ 首轮 6 批后追加"粗糙表述的规范化：大批量（100–300 张）多 Agents 并行读图能力**保留并增强**为一等能力，对齐 Codex 版 `execute in waves` 思想。

**派发约定**：
- 给每个 subagent 一段 **bounded manifest slice**：绝对图片路径 + 稳定 manifest index（Claude Code 侧通过 Agent 工具 prompt 传入；Codex 侧用 `items` 的 `local_image` 条目）。
- **同一张图不派给多个 subagent**，除非在校验某个不确定读数。
- subagent 调用 prompt 模板：

  ```
  分析这批图片用于 Obsidian LLM Wiki 更新。只读，不编辑文件。
  每张图按九字段输出契约返回一个 section，然后给批次总结。
  严格保留 manifest index 与文件名。
  ```

**每张图输出契约（九字段）**：`manifest_index` / `filename` / `visible_text`（可见文字）/ `page_topic`（主题）/ `key_points`（关键要点）/ `diagrams_flows_ui`（图表/流程/UI 元素）/ `insights`（可提炼洞见）/ `confidence`（高/中/低）/ `unreadable_areas`（无法识别或不确定区域）。

**每批次输出（四件套）**：`batch_summary`（批次总结）/ `repeated_ideas`（跨图重复观点）/ `contradictions_or_low_confidence`（矛盾或低置信读数）/ `wiki_section_candidates`（建议归入章节：`图片内容解析` / `资料总结` / `洞见` / `方法论提炼` / `最佳实践` / `金句精选`）。

**归并对账**：subagent（含跨波次）返回后，**先比对 filename 与 manifest index** 再合成，防止张冠李戴、缺页或重复解析。

## 运行时与网关适配（视觉通道 + 读图降级 + 大文件日志）

本 Skill 默认假设主 agent 与只读 subagent 的 `Read` 能正常解析图片像素。但**第三方网关（如智谱 GLM、MiniMax 等兼容 Anthropic 协议的网关）的多模态下推链路未必启用**：实测在某些网关下，`Read` 图片只返回"文件已上传至 CDN"的文本回执（含一个 URL），**不向模型返回视觉内容**——主 agent 与 subagent 都"看不见"图。此时**视觉理解 MCP**（如智谱 `zai-mcp-server`，接入 GLM-4.6V）可作为独立于网关的视觉通道。本节规定三级视觉通道（`Read` → 视觉 MCP → 降级）的探测与降级流程，避免空转、避免虚构。

### 视觉理解 MCP 通道（zai-mcp-server）

第三方网关 `Read` 失效时的首选兜底视觉通道：智谱官方 Local MCP Server `zai-mcp-server`（npm 包 `@z_ai/mcp-server`，接入 GLM-4.6V；官方文档 https://docs.bigmodel.cn/cn/coding-plan/mcp/vision-mcp-server ），配置于 `~/.claude.json` 顶层 `mcpServers`。安装步骤与 API Key 配置说明见本 skill README 的「视觉 MCP 配置（可选）」一节；**配置示例中的 API Key 一律用占位符，绝不把真实密钥写进任何文件或日志**。

**工具清单与 wiki 九字段映射**（以实际安装的工具名为准；智谱文档中的 `image_analysis` / `video_analysis` 对应实际安装名 `analyze_image` / `analyze_video`）：

| 实际工具名（`mcp__zai-mcp-server__` 前缀） | 用途 | 映射到九字段输出契约 |
|---|---|---|
| `analyze_image` | 通用图像理解（兜底）；`image_source` 支持本地绝对路径与远程 URL | 全字段 |
| `extract_text_from_screenshot` | OCR 文字提取（可指定 programming_language） | `visible_text` |
| `understand_technical_diagram` | 架构/流程/UML/ER 图结构化解读 | `diagrams_flows_ui` |
| `analyze_data_visualization` | 图表/仪表盘数据提炼 | `diagrams_flows_ui` + `key_points` |
| `diagnose_error_screenshot` | 错误弹窗/堆栈/日志截图诊断 | wiki 场景少用 |
| `ui_to_artifact` | UI 截图转代码/提示词/设计规范 | wiki 场景少用 |
| `ui_diff_check` | 对比两张 UI 截图差异 | 校验场景 |
| `analyze_video` | 视频解析；本地文件 ≤8MB，MP4/MOV/M4V | 拓展能力（如视频类领域） |

**调用约定**：

- `image_source` 传**本地绝对路径**（中文与空格路径直接传，不走 PowerShell 管道）；单图单工具调用，逐张按 manifest index 对账。
- 按图型选工具：常规截图/扫描件用 `analyze_image` 兜底；文字密集图优先 `extract_text_from_screenshot`；架构/流程图优先 `understand_technical_diagram`；统计图表优先 `analyze_data_visualization`。
- **隐私边界**：视觉 MCP 是云端通道，图片内容会上送智谱服务器处理；涉及敏感资料时先经用户确认再走此通道。
- **subagent 授权**：要让只读 subagent（如 `image-reader`）在此通道下读图，项目需在其 agent 定义的 `tools` 中显式授予对应 `mcp__zai-mcp-server__*` 工具；未授予时由主线程分批逐张调用。

### 图片读取能力探测（读图前必做一次）

- **顺序探测**（用同一张代表性图，优先概念图、含文字最多的图，如"X VS Y"对比图）：
  1. **`Read` 单图探测**：返回内容含图片视觉信息 → **Read 视觉通道可用**，走正常 subagent 批量分析（§Subagent 批量分析）。
  2. **视觉 MCP 单图探测**：`Read` 仅返回 `... has been uploaded to CDN and is available at: https://...` 文本回执时，调 `mcp__zai-mcp-server__analyze_image` 并把该图**本地绝对路径**传入 `image_source`：返回真实视觉内容 → **视觉 MCP 通道可用**，按 §视觉理解 MCP 通道 的调用约定读图。
  3. 两级探测都失败（MCP 未配置 / 调用报错 / 无视觉内容）→ 进入降级流程。
- **通道能力矩阵**（集中维护，验证后更新；顺序探测机制使其自纠正，矩阵过期也不影响判断）：
  - 官方 Anthropic API：`Read` 视觉可用（默认）。
  - 智谱 GLM 网关：`Read` **已验证不可用**（仅返回 CDN URL 回执，无视觉内容；主线程与 subagent 同失效）；`zai-mcp-server` 视觉 MCP **已验证可用**（2026-08-19 本地实测：`analyze_image` 以含中文与空格的本地绝对路径成功返回完整视觉描述与文字转录）。
  - `4_5v_mcp`（GLM Coding Plan 服务端内置的 image_analysis 通道）：仅支持远程 URL，本地 raw 图片不适用。
  - MiniMax 网关：**未验证**（待测；若在此网关下，先做顺序探测，把结果回写本节）。
- 探测结果写入当次 `log.md` 条目（视觉通道：Read 可用 / 视觉 MCP 可用 / 均不可用 + 网关名）。

### 视觉不可用时的降级流程

**两条视觉通道（`Read` 与视觉 MCP）都不可用时**才进入降级。降级**不等于放弃**：image manifest 的建立、文件名/顺序/来源匹配、缺失与重名检测都是**文件系统层**操作，不需要视觉。降级按六步：

1. **照常建 image manifest**（§图片密集资料分析）：按文档顺序提取 `![[...]]`、解析短文件名、与 raw 目录对账、检测重名/缺失/越界。manifest 完整性与视觉无关。
2. **视觉识别字段全部标"视觉未识别"**：`visible_text` / `key_points` / `diagrams_flows_ui` / `insights` 等"需要看图"的字段不填、不猜，统一标注"视觉未识别（当前网关多模态通道与视觉 MCP 均不可用）"。
3. **基于已有文字做高维度提炼**：页面已有逐字稿/正文/结构表/金句等文字（典型如飞书 doc 抓取页）时，完全可基于这些文字完成"资料总结/洞见/方法论提炼/最佳实践/金句精选"——它们不依赖图片视觉。
4. **概念图概念补充须标注来源**：某张概念图（如"平等 VS 公正"对比图）承载的概念若在正文已有文字阐释，可引用正文作补充，但必须明确写"基于正文，非图像识别"。
5. **不重复空转**：视觉不可用时**不再**派发读图 subagent、也不再逐张调用视觉 MCP（派了也是空回执或报错）；把"图片视觉内容待多模态通道或视觉 MCP 恢复后补录精确转写"记为**未决项**，写进 `log.md` 与页面"图片内容解析"节。
6. **不虚构**：绝不依据文件名或上下文猜测图中具体文字、人物、数字、颜色并当作识别结果写入。

> 项目侧若已声明视觉通道与降级路径（如项目 `CLAUDE.md` 的 Claude Code 适配章节），以项目声明为准；本节是通用兜底。

### log.md 追加（大文件安全）

`log.md` 随维护累积会变得很大（实测单个 vault 的 `log.md` 可达数百 KB）。`Read` 工具有大小上限（约 256KB），大 `log.md` **整文件读不了**，也就无法用"读末尾 → Edit 锚点"的方式追加。追加流程：

- **首选：直接追加到文件末尾（append-only，无需锚点）**。`log.md` 是 append-only，新条目永远加在 EOF，不需要读旧内容：
  - bash（Git Bash / WSL）——用引号封闭定界符的 heredoc，防变量展开，内部反引号/代码栏安全：
    ```bash
    cat >> "路径/log.md" <<'LOGEOF'

    ## [YYYY-MM-DD] <操作> | <标题>

    - <条目内容>
    LOGEOF
    ```
  - PowerShell——`Add-Content` 默认追加，中文/带空格路径用 `-LiteralPath`，UTF-8 编码，不走管道（与既有"不通过管道喂 Python"安全规则一致）：
    ```powershell
    Add-Content -LiteralPath "路径\log.md" -Encoding UTF8 -Value @"

    ## [YYYY-MM-DD] <操作> | <标题>

    - <条目内容>
    "@
    ```
- **次选：Edit + tail 锚点**（文件仍可被 `Read` 时）：`tail -n 5` 取末尾几行作 Edit 的 `old_string`（取含独特上下文的行保证全文唯一，必要时多取几行），再 Edit 追加。
- **禁止**：为追加条目而 `Read` 整个大 `log.md`（触发大小上限失败并浪费上下文）。
- **抽查**：追加后用 `tail -n 3` 或 `grep` 确认新条目落位正确即可，不必整读。

> 说明：用户直觉里的"用 tail 做新增"映射为"shell 文件末操作"——`tail` 用于取锚点/抽查，实际写入用 `>>` / `Add-Content`（tail 本身只读不写）。

## Index Metadata And Statistics

`index.md` 是知识库的内容目录，**LLM 维护**。它有固定的**顶部维护块**、**底部统计行**与**索引健康行**，本节规定其精确格式、字段语义、六变量计数口径、同步契约与校验规则。所有写命令（ingest / optimize / extract-thinking-frameworks / index / migrate / delete / query-归档）以及 lint 校验都必须遵守本节。

> **不在 `index.md` 上引入 YAML frontmatter**。日期、计数、操作摘要都由正文/斜体/引用块承载；变更历史由 `log.md` 承担。
>
> 本节使用**六个变量**（与项目 schema、实际 vault 页脚一致）：三权威变量 `indexed_page_count` / `wiki_file_count` / `registered_domain_count`，三健康变量 `missing_count` / `broken_count` / `duplicate_count`。**不得用 `wiki_file_count` 代替 `indexed_page_count`**——两者必须独立验证。

### Index 文件结构总览

`index.md` 由四部分组成，按出现顺序固定：

1. **顶部维护块**（2 个 `>` 引用行 + 1 个 `---` 分隔线）— 见 §Index 顶部维护块
2. **章节主体**（一个或多个 `## <领域路径>` 章节；每个章节下 1 张三列表，列头固定为 `| 页面 | 摘要 | 标签 |`、分隔行 `|---|---|`）— 见 §Index 章节与表格规范
3. **底部统计行**（倒数第二行的 `>` 索引健康行 + 最后一行的斜体统计行）— 见 §Index 底部统计与索引健康行

各部分之间**必须**用 `---` 分隔线隔开；不允许出现其他段落、HTML 注释、或 H1 之外的标题（H2 章节允许）。

### Index 顶部维护块

#### 字面模板

```markdown
# 知识库索引

> 由 LLM 维护。上次更新：<YYYY-MM-DD>（<简洁动作摘要>）。
> 格式：`[[页面标题]]` — 一句话摘要

---
```

#### 字段语义

- `<YYYY-MM-DD>`：本次更新本地日期（4 位年 - 2 位月 - 2 位日，零填充）。**不变量**：必须与底部统计行的日期、`log.md` 本次条目日期、今天本地日期**字面一致**。
- `<简洁动作摘要>`：本次动作的动词短语；可含命令名、涉及页面/Schema 名；涉及多文件时可缩为 `A.md、B.md 等 N 个 wiki 页面`。**不再强求文件列表**（如本次仅刷 Schema，摘要可只写一句）。
- 第 2 行 `> 格式：...` 是**只读脚注**，永远不修改（除非全文件结构改版）。

**操作摘要建议用语**（非字面契约，仅供措辞参考）：

| 场景 | 建议摘要 |
|---|---|
| `ingest` / `query-归档` | `同步索引：新增 1 个页面（<页面名>）` |
| `optimize`（摘要未变） | `同步索引：刷新 1 个页面（<页面名>）` |
| `optimize`（摘要已变） | `同步索引：更新 1 个页面（<页面名> 摘要变）` |
| `extract-thinking-frameworks` | `同步索引：新增 1 个页面（<框架名>，归入 提炼思维）` |
| `index`（全量重建） | `同步索引：补登 X 个页面、修正 Y 个链接、去重 Z 个重复条目`（X/Y/Z 为本次 diff；必要时附 `统计漂移修正`） |
| `migrate` | `同步索引：迁移 N 个页面至 wiki/<领域>/` |
| `delete` | `同步索引：移除 1 个页面（<页面名>）` |
| 补录既有页面 | `同步索引：补录既有页面 <页面名>` |
| Schema 同步（非 wiki 变更） | `同步 AGENTS.md 与 CLAUDE.md Schema，并统一索引统计口径` |
| 完全不写 index 的只读操作（`query` 未归档、`lint` 不写） | 顶部维护块**整体不更新**，日期保持上一次；但 `log.md` 必须有 "index.md：已检查，无需本次修改" |

### Index 章节与表格规范

- 一律用 `## <领域路径>` 二级标题；领域路径用 ` / ` 分段（半角斜杠 + 两侧空格）。
- 顶级段必须与 schema `## 领域注册表` 的"领域"列**语义一致**（不强制字面相等，因为 schema 可能有"一堂/创业者修炼"而 index 有"一堂"）。
- 同级章节按顶级段 → 二级段字典序排列；用户手动调整顺序时**尊重用户**，但**禁止出现空章节**（只有标题无表格）。
- 表格列头**必须**固定为 `| 页面 | 摘要 | 标签 |`，分隔行**必须**为 `|---|---|`。
- 数据行**必须**形如 `| [[<页面标题>]] | <一句话摘要> | <inline tags> |`。
- 一行 = 一个 wiki 页面。**禁止同一行两个 `[[]]`**。
- 同一 `##` 章节下**禁止出现重复行**（按 `[[<页面标题>]]` 字段去重）。
- 摘要列**只放摘要**，不写正文片段、不放链接（链接在 `## 相关` 章节正文里）。

### Index 底部统计与索引健康行

文件**最后两行**固定为：倒数第二行 `>` 索引健康行，最后一行斜体统计行。

#### 字面模板

```markdown
_统计：{indexed_page_count} 个已索引页面 | {wiki_file_count} 个 Wiki 文件 | {registered_domain_count} 个注册领域 | 上次更新于 YYYY-MM-DD_

> 索引健康：未收录 {missing_count} | Markdown 断链 {broken_count} | 重复条目 {duplicate_count}；`.canvas`、示例占位和 `raw/...` 链接不计入页面数。
```

#### 字段语义

- **统计行**（斜体，前后各 1 `_`，文件最后一行）：三个权威变量 + 日期。
- **索引健康行**（`>` 引用块，倒数第二行，永远在统计行之前一行）：三个健康变量 + 尾部说明。尾部说明文字（`.canvas`、示例占位、`raw/...` 不计入页面数）是只读脚注，不修改。
- `<YYYY-MM-DD>`：与顶部维护块**字面一致**。

### Index 六变量计数口径

#### 三权威变量

| 变量 | 定义 | 计数口径 |
|---|---|---|
| `indexed_page_count` | 可解析到真实 `wiki/**/*.md` 且**去重后**的索引条目数 | 抽取 index 所有 `\| [[<title>]] \|` 数据行的 title → 按 stem（去 `.md`）在 `wiki/**/*.md` 查找 → 命中且唯一则计入；同一 wiki 文件多次出现只计 1 次 |
| `wiki_file_count` | 实际 `wiki/**/*.md` 文件数 | glob 扫描，排除 `index.md` / `log.md` / `*.canvas` / `templates/` / `assets/` |
| `registered_domain_count` | 领域注册表数据行数 | 读 schema `## 领域注册表` 表，去表头与分隔行后的数据行数 |

#### 三健康变量

| 变量 | 定义 | 含义 |
|---|---|---|
| `missing_count` | 有 wiki 文件但无唯一可解析索引条目覆盖 | 应补录；>0 报告或补录 |
| `broken_count` | 无法唯一解析且不属于排除项的 index 链接 | title 未命中、或命中华歧义；应修正或摘除 |
| `duplicate_count` | 同一真实 wiki 页面在 index 中的额外重复条目 | 同 path 被 ≥2 条目解析 → +(出现数 − 1)；首次出现不计 |

**机检**：
- **快校（lint 用，上限预警）**：保留旧 awk 一行版，重命名为 "raw entry count"（仅数 `| [[` 候选行，不去重、不解析），作为漂移预警的快检上限——**不是** `indexed_page_count` 的精确值。
- **精校（所有写命令用）**：扫 `wiki/**/*.md` 建 `{stem: path}` 字典 → 解析 index 数据行 title → 命中（dedupe by path，记 `indexed_page_count`）/ 未命中（`broken_count`）/ 字典中未被命中（`missing_count`）/ 同 path 重复（`duplicate_count`）；`wiki_file_count` = 字典 size；`registered_domain_count` = schema 注册表数据行数。

```bash
# 快校 awk 一行版（raw entry count 上限，非精确 indexed_page_count）
awk '/^\| 页面 \| 摘要 \| 标签 \|/{t=1;next} t==1 && /^\|---/{t=2;next} t==2 && /^\| \[\[/ {c++} t==2 && /^## /{t=0} END{print c+0}' index.md
```

**排除项**（不计入页面数）：`.canvas` 文件、图片、附件、`raw/...` 源链接、生成产物、外部链接、schema 文件、`[[页面标题]]` 这类示例占位、`templates/` 与 `assets/` 下的模板。

#### 计数漂移处置

- **首次补录**（`补录既有页面` / first-time index backfill）：wiki 文件存在但 index 无条目 → 加条目，`indexed_page_count` +1，log 标 `补录既有页面`。
- **统计漂移修正**（`统计漂移修正`）：旧 footer 与实际扫描结果不符 → 用新扫描值覆盖全部六个变量，log 标 `统计漂移修正`；**绝不**在旧值上递增。
- **仅摘要/标签/路径文字变化**（链接解析与去重未变）：`indexed_page_count` 不变。
- **创建/删除/迁移/改名/归档/去索引/补录**：六变量全部重算。

### 同步契约 / 增量与全量分工

**同步契约不变量**：

```
顶部 <YYYY-MM-DD>  ==  底部统计行 <YYYY-MM-DD>  ==  log.md 本次条目日期  ==  今天（本地）
indexed_page_count  ==  当次扫描去重后解析的 index 条目数（不沿用旧值）
wiki_file_count     ==  当次 wiki/**/*.md 文件数
registered_domain_count ==  schema 领域注册表数据行数
missing_count / broken_count / duplicate_count ==  当次扫描结果
统计行与索引健康行各只出现 1 次
```

**写命令的标准操作流程**（落盘 index.md 前必走）：

1. 完成 wiki 页面变更（创建/修改/删除）
2. 决定 `<简洁动作摘要>`（按 §Index 顶部维护块 建议用语表，允许简洁版）
3. 在 `index.md` 上做增量修改
4. 运行 §六变量计数口径 精校 → 得六变量新值
5. 顶部维护块 + 底部统计行 + 索引健康行 **同一次编辑**同步替换（三处日期字面一致）
6. 若涉及双入口 schema 变更（如新领域），同步编辑 `AGENTS.md` + `CLAUDE.md` + 验 SHA-256
7. `log.md` 追加一条最终记录（含 `AGENTS.md` / `CLAUDE.md` / `index.md` / frontmatter 四项 + 六变量 + `indexed_page_count` 变化/不变/漂移修正 标识）
8. 写后自检（快校 awk + 精校；统计行与健康行各只出现 1 次）

**增量 vs 全量分工**：

| 命令 | 模式 | 落盘动作 |
|---|---|---|
| `ingest` / `optimize` / `extract-thinking-frameworks` / `migrate` / `delete` / `query-归档` | **增量** | 在对应 `## <领域>` 章节追加/修改/删除一行；刷新顶部维护块 + 底部统计行 + 索引健康行 |
| `/index` | **全量** | 完整扫描 `wiki/**/*.md`，重算后整文件重写；与增量互为补集 |
| `/lint` | **不动 index**，只校验 | 见 §Index lint 校验规则 |

**何时必须走全量（`/index`）**（增量无法修复时）：

- 顶部日期 ≠ 底部统计行日期
- `indexed_page_count` ≠ 扫描结果
- `wiki_file_count` ≠ 扫描结果
- `registered_domain_count` ≠ schema 注册表行数
- 任一健康变量 ≠ 扫描结果
- 同一 `##` 章节下出现重复行
- 顶级段集合 vs schema 领域注册表集合差集非空
- 用户显式要求"重建索引"

### Index lint 校验规则

`/obsidian-llm-wiki lint` 在原有步骤之上**追加 index.md 专项校验**：

1. 解析 `index.md` 抽取顶部维护块、底部统计行、索引健康行、全部 H2 章节。
2. 顶部维护块字面合规（正则 `^> 由 LLM 维护\.上次更新：(\d{4}-\d{2}-\d{2})（.+）\n> 格式：.+`）。
3. **底部统计行**字面合规（正则三变量版）：`^_统计：(\d+) 个已索引页面 \| (\d+) 个 Wiki 文件 \| (\d+) 个注册领域 \| 上次更新于 (\d{4}-\d{2}-\d{2})_$`。
4. **索引健康行**字面合规（正则）：`^> 索引健康：未收录 (\d+) \| Markdown 断链 (\d+) \| 重复条目 (\d+)；.+。$`。
5. 顶部日期 = 底部统计行日期 = 今天。
6. **快校**：awk 数候选行数 ≥ `indexed_page_count`（上限校验）。
7. **精校**：按 §六变量计数口径 扫描得六变量；分别与统计行三数 + 健康行三数核对。
8. 校验统计行与索引健康行**各只出现 1 次**（grep 计数 = 1）。
9. 校验每个 `## <领域>` 章节下有且仅有一张表，表头/分隔行/数据行格式合规。
10. 校验同一章节内数据行不重复（按 `[[<页面标题>]]` 去重）。
11. 校验顶级段集合与 schema `## 领域注册表` 集合的差集，报告。
12. **双入口 schema 字节一致**：存在 `AGENTS.md` + `CLAUDE.md` 时校验两文件字节相同（或按 vault 声明的契约）；不一致则报告。
13. 报告格式：每条不通过一项给出一行"`index lint 失败：<原因> + 建议动作（增量修复 / 走 `/index` 全量重建 / 双入口同步并验 SHA-256）`"。
14. **lint 不自动修改 `index.md`**；但若全量重建条件成立，提示用户"建议运行 `/obsidian-llm-wiki index`"。

### Index 反例 / 常见错误

- **A**：顶部维护块只有 1 个 `>` 引用行（漏了"格式：..."脚注）→ lint 报"顶部维护块缺格式说明行"。
- **B**：底部统计行用了粗体 `**统计：...**` → grep 难定位；lint 报"底部统计行非斜体"。
- **B'**：底部统计行用旧两变量模板 `_统计：421 个页面 | 18 个领域 | ..._` → lint 报"底部统计行非三变量模板，疑似旧版残留"。
- **C**：日期写成 `2026/6/23`（斜杠、无零填充）→ 不符合契约；lint 报"日期格式不符 YYYY-MM-DD"。
- **D**：`indexed_page_count` 与扫描结果差 N → lint 报"`indexed_page_count` 漂移"，建议走 `/index` 全量重建。
- **E**：`## 一堂 / 创业者修炼` 与 `## 一堂/创业者修炼`（" / "两侧少空格）混用 → 顶级段解析不一致；lint 报"领域路径格式不一致"。
- **F**：在 `index.md` 中插入 H1 之外的 H2/H3 章节（如 `### 索引说明`）→ 不在契约内；lint 报"未声明的 H3 章节"。
- **G**：在表格行里写两个 `[[]]`（如 `| [[A]] 与 [[B]] | ... | ... |`）→ 一个数据行被当两个页面；lint 报"数据行多 wiki 链接"。
- **H**：`optimize` 改了页面摘要但忘了刷 `index.md` 的摘要列 → 摘要与 index 不一致；`/lint` 应同时校验"页面 frontmatter 一句话摘要"与"`index.md` 同行的摘要列"内容一致。
- **I**：缺少索引健康行 → lint 报"缺索引健康行；按 §Index 底部统计与索引健康行 补齐"。
- **J**：双入口 schema SHA-256 不等 → lint 报"AGENTS.md 与 CLAUDE.md 字节不一致；按 vault 契约同步两文件并验 SHA-256"。
- **K**：用 `wiki_file_count` 代替 `indexed_page_count` 填入统计行 → lint 报"不得用 `wiki_file_count` 替 `indexed_page_count`；两者必须独立验证"。

## 命令

### /obsidian-llm-wiki ingest \<source\>

处理 `raw/` 中的新来源，集成到 wiki。

1. 确认来源文件在 `raw/` 对应目录中
2. **文档预处理**（条件性）：PDF/DOCX/PPTX/XLSX 或大量图片，`scripts/` 就位时用 `.venv` 预处理并建立 manifest；未就位时 PDF 用 Read 的 `pages` 参数直读
3. **图片密集分析**：图片密集资料按 image manifest 分析；先做视觉通道顺序探测（`Read` → 视觉 MCP，见「运行时与网关适配」），超过 10 张派只读 subagent 并行分析，100–300 张以波次推进（见「Subagent 批量分析」）
4. **核对 manifest**：阅读/分析时核对覆盖率、顺序、缺失、重名，异常先报告
5. 与用户讨论关键要点
6. 在 `wiki/` 对应目录创建摘要页面：
   - 读项目 schema 确定领域和路径映射
   - 选合适模板（项目 `templates/` 或 Skill `assets/`）
   - 加 YAML frontmatter（七字段，按 schema 规范）
   - 加 inline tags（与 frontmatter 匹配）
   - 含一句话摘要
   - 图片分析结果整理进 `图片内容解析` / `资料总结` / `洞见` / `方法论提炼` / `最佳实践` / `金句精选` 六节
   - 加「相关」和「来源」部分
7. 更新与新内容相关的已有 wiki 页面
8. **运行强制维护遍历**。若 `index.md` 改变（新页面 → `indexed_page_count` +1；补录既有页面 → +1 且 log 标 `补录既有页面`；仅摘要/标签变 → 不变），按 §Index Metadata And Statistics 重算六变量，**同一次编辑**刷新顶部维护块 + 底部统计行 + 索引健康行；追加 `log.md` 条目 `## [YYYY-MM-DD] ingest | <标题>`，日期与 index 顶部/底部字面一致，含 AGENTS/CLAUDE/index/frontmatter 四项 + 六变量 + `indexed_page_count` 变化标识。

### /obsidian-llm-wiki query \<问题\>

使用 wiki 回答问题。

1. 读项目 schema 了解架构
2. 读 `index.md` 了解可用内容
3. 从索引定位相关 wiki 页面
4. 读相关页面
5. 综合答案，引用页面 `[[标题]]`
6. **运行强制维护遍历**（query 默认只读 → **只报告** schema/index gaps，不自动修改）
7. 询问用户是否将答案归档为新 wiki 页面；若是，创建页面并更新 index.md（按 §Index Metadata And Statistics 重算六变量）和 log.md

### /obsidian-llm-wiki optimize \<page\>

优化已有 wiki 页面（结构、表达、交叉引用），**不删除已有图片嵌入**，不破坏已有 wiki 链接。

1. 读目标页面，读其 `sources` 对应的 raw 资料
2. 页面图片 ≤10 张：读全部图片后优化；>10 张：先确认用户是否读全部，或仅基于已有文字优化
3. 优化 frontmatter（补缺失字段、更新 `updated`；frontmatter 修复是结构例外，append-only 体优化时仍可置正文前）、结构、表达
4. 追加内容（如需）插在 `## 相关` 之前；图片分析结果整理进六节
5. 检查并补充缺失的交叉引用
6. **运行强制维护遍历**。若 `index.md` 改变：摘要未变 → 顶部维护块摘要 = `同步索引：刷新 1 个页面（<页面名>）`；摘要已变 → `同步索引：更新 1 个页面（<页面名> 摘要变）`；**`indexed_page_count` 不变**（除非链接解析或去重变化）。按 §Index Metadata And Statistics 重算六变量并同步三处；追加 `log.md` 条目 `## [YYYY-MM-DD] optimize | <标题>`，日期字面一致。

### /obsidian-llm-wiki extract-thinking-frameworks

从 wiki 内容中提炼通用方法论与思维模型，归入 `wiki/提炼思维/`（无 raw 层）。

1. 扫描 `wiki/` 找反复出现的方法论、框架、模型
2. 与用户讨论提炼方向
3. 在 `wiki/提炼思维/` 创建独立页面（frontmatter `domain: 提炼思维`）
4. 在源页面添加 `[[提炼出的框架]]` 交叉引用
5. **运行强制维护遍历**。若 `index.md` 改变：在 `## 提炼思维` 章节追加一行；重算六变量；`registered_domain_count` 按 schema 注册表行数取（"提炼思维"若首次进注册表则 +1）；追加 `log.md` 条目 `## [YYYY-MM-DD] extract-thinking-frameworks | <标题>`，日期字面一致。

### /obsidian-llm-wiki lint

健康检查 wiki。

1. 读 `index.md`，验证每个列出的页面存在
2. 读每个 wiki 页面，检查：YAML frontmatter 存在且七字段齐全；frontmatter tags 与 inline tags 一致；页面至少 2 个出站 wiki 链接；无断裂链接；同主题页面间无矛盾
3. 找孤立页面（无入链）
4. 找值得拥有独立页面的内联提及
5. 检查过期内容（30+ 天未更新）
6. 向用户报告发现
7. 追加 lint 报告到 `log.md`
8. **`index.md` 专项校验**（详见 §Index Metadata And Statistics §Index lint 校验规则，六变量口径）：顶部维护块正则、底部统计行三变量正则、索引健康行正则、三处日期一致、六变量精校、统计行与健康行各只 1 次、表格格式、同章节去重、顶级段 vs 注册表差集、双入口 schema 字节一致。**不自动修改 `index.md`**；全量重建条件成立时提示 `/index`。

### /obsidian-llm-wiki index

从当前 wiki 状态**全量重建** `index.md`。与各写命令的"增量更新"互为补集；本命令是兜底 / 一致性修复入口。

1. 扫描 `wiki/**/*.md`，跳过 `index.md` / `log.md` / `*.canvas` / `templates/` / `assets/`
2. 对每个 .md 读 YAML frontmatter 抽 `title` / `domain` / `created` / `updated`；读正文第一段非空行作"一句话摘要"；读 `tags` 作 inline tags
3. 按 `domain` 分到 `## <domain>` 顶级段；二级段从文件相对路径 `wiki/<domain>/...` 推断（如 `wiki/AI/编程出海/技术/上线/落地页/X.md` → `## AI / 编程出海 / 技术 / 上线 / 落地页`）。推断失败时归入 `## <domain> / 其他`
4. 按 §Index 章节与表格规范 排序并写入三列表
5. 按 §六变量计数口径 重算六个变量
6. 按 §Index 顶部维护块 / §Index 底部统计与索引健康行 模板写入三处，操作摘要 = `同步索引：补登 X 个页面、修正 Y 个链接、去重 Z 个重复条目`（X/Y/Z 为本次 diff；必要时附 `统计漂移修正`）
7. **运行强制维护遍历**；校验三权威变量 + 三健康变量、统计行与健康行各只 1 次、三处日期字面一致；将本次 index 重建条目追加到 `log.md`，记录 `indexed_page_count` 变化/不变/漂移修正标识

**不变量**：本命令产物必须通过 §Index lint 校验规则 的所有检查。

### /obsidian-llm-wiki migrate

一次性迁移助手，把已有 Obsidian 笔记迁到 LLM Wiki 模式。

1. 扫描项目目录，找不在 `raw/` 和 `wiki/` 中的 .md 文件
2. 与用户确认每个文件属于哪个领域
3. 对每个文件：读内容 → 提取 inline tags → 生成 frontmatter（按 schema 规范）→ 确定目标（raw/ 或 wiki/）→ 写入新位置 → **同步 `index.md`**（按 §Index Metadata And Statistics，操作摘要 = `同步索引：迁移 N 个页面至 wiki/<领域>/`，N = 本次累计的 wiki 写入数；重算六变量）→ 记录迁移日志
4. 若迁移引入新领域导致双入口 schema 变更，**同步编辑 `AGENTS.md` + `CLAUDE.md` + 验 SHA-256**
5. 所有文件迁移完成后，**建议运行 `/obsidian-llm-wiki index` 全量重建**（增量可能因目录拓扑变化漂移），并把"全量重建"作为迁移日志的最后一条

### /obsidian-llm-wiki delete \<page\>

删除 wiki 页面（**不动 raw/**）。删除前：确认无其他页面的入链，或有则提示用户处理断链。删除动作：用 `Remove-Item -LiteralPath "<绝对路径>"`，禁通配符/`-Recurse`/批量/目录删除。删除后**运行强制维护遍历**：在对应 `## <领域>` 章节删除该行；检查相关链接/反向链接/index 是否需要更新；`indexed_page_count` 变化则重算六变量；顶部维护块摘要 = `同步索引：移除 1 个页面（<页面名>）`；追加 `log.md` 条目 `## [YYYY-MM-DD] delete | <标题>`，日期与 index 顶部/底部字面一致。

## 排版规范

所有 wiki 页面应遵循以下排版标准。

### 标题层级

- 页面不使用 H1（`#`），标题由 frontmatter `title` 定义
- 正文从 H2（`##`）开始，层级严格递进不跳级
- 同一页面中 H2 之间保持语义平行

### 列表格式

- 无序列表统一使用 `-`（不混用 `*` 和 `+`）
- 嵌套缩进 2 个空格
- 任务列表使用 `- [ ]` 和 `- [x]`

### 表格

- 必须包含表头行和分隔行
- 仅在数据对比或多维度信息时使用，简单列表不转为表格

### Callout

使用 Obsidian callout 替代普通引用表达特殊语义：`> [!note]`、`> [!tip]`、`> [!warning]`、`> [!info]`、`> [!quote]`。一句话摘要仍用普通引用（`> 摘要`），不使用 callout。

### 代码块

- 行内代码用反引号包裹命令、文件名
- 代码块指定语言标识（如 ` ```python `、` ```bash `）

### 图片

- 默认不指定尺寸（`![[图.png]]`），让 Obsidian 自适应
- 信息密度高的图表可限宽：`![[图.png|400]]`
- 不指定高度（保持纵横比）

## 页面要求

**必需结构元数据**（缺失即视为结构缺口，由强制维护遍历修复）：

1. YAML frontmatter 作为文件第一行/块，`---` 起始，含七字段：`title` / `created` / `updated` / `domain` / `tags` / `sources` / `status`
2. Inline tags（如使用）与 frontmatter tags 一致
3. Tags 规范化：标签片段内空格用 `_`（如 `一堂/AI_Live`）

**推荐内容**（服从资料类型、已有页面结构与用户作用域；**不**为 query-only 或轻量维护任务强制扩写）：

1. 一句话摘要（以 `>` 引用格式）
2. 正文内容
3. `## 相关` — wiki 链接到相关页面（每页至少 2 个可解析出链）
4. `## 来源` — 引用 raw 来源（schema 定义的无 raw 领域如 `提炼思维` 可省）

> frontmatter 是结构例外：append-only / 保留正文约束不阻止把缺失 frontmatter 修复到第一行（见 §Frontmatter 与 Tag 规范化）。

## 守则

- 绝不修改 `raw/` 下的文件
- 覆盖已有 wiki 内容前须确认；优化时不删除已有 `![[]]` 图片嵌入
- `log.md` 条目 append-only
- 保持中文为主要内容语言
- 不确定时询问用户
- 所有路径和领域从项目 schema（`AGENTS.md` / `CLAUDE.md`）读取，不硬编码
- **双入口 schema 字节一致**：声明契约时 `AGENTS.md` 与 `CLAUDE.md` 必须字节相同；结构变更同步两文件并验 SHA-256
- 派出的 subagent 只读，不修改 raw/wiki/index/log/schema/.claude
- 图片重名/缺失/无法定位一律先报告，不猜测
- **不虚构**来源、数据、引用或验证结果
- 中文路径与带空格路径用 `-LiteralPath` 或显式参数，不走 PowerShell 管道；不修改 PATH、不重装 Python、不调用户目录 Python
- `log.md` 条目至少含：日期与任务名 / 增改删文件 / 是否检查 `AGENTS.md` + `CLAUDE.md` / 是否检查 frontmatter + 图片嵌入 + `index.md` + 统计 / 关键验证结果与未决项；同一任务只追加一条最终记录
