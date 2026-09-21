---
title: "obsidian-llm-wiki 实战指令手册（范例）"
created: 2026-09-21
updated: 2026-09-21
domain: 提炼思维
tags: [type/参考, domain/提炼思维]
sources: []
status: active
---

# obsidian-llm-wiki 实战指令手册（范例）

> 本文件是脱敏范例：展示向 LLM 下达知识库维护指令的写法。所有路径、领域、页面名均为占位，使用时替换为你自己的；真实资料内容不入公开仓库。

## 配套范例文件

| 文件 | 用途 |
|---|---|
| `examples/AGENTS.example.md` | schema 范例，重命名为 `AGENTS.md` / `CLAUDE.md` 放 vault 根（双入口字节一致） |
| `examples/index.example.md` | `index.md` 范例（六变量占位符页脚） |
| `examples/log.example.md` | `log.md` 范例（init 示例条目 + 全字段模板条目） |
| `examples/prompt-handbook.example.md` | 本文件 |

## 示例领域路径

| 占位领域 | raw | wiki |
|---|---|---|
| 读书笔记 | `raw/读书笔记/` | `wiki/读书笔记/` |
| AI | `raw/AI/` | `wiki/AI/` |
| 项目资料 | `raw/项目资料/` | `wiki/项目资料/` |
| 提炼思维 | — | `wiki/提炼思维/` |

## 一、怎么写好指令

### 1.1 先说任务意图，再给命令

| 你想做 | 直接说 |
|---|---|
| 新资料入库 | "把 `raw/AI/<资料名>/` 入库" |
| 增强既有页面 | "给 `wiki/AI/<页面>.md` 做内容增强，raw 目录是 `raw/AI/<资料名>/`" |
| 页面要改写表达 | "优化 `wiki/AI/<页面>.md`，允许整理结构与表达" |
| 只读问答 | "问：……（只读，不改任何文件）" |
| 体检 | "跑一次 lint，只报告不修复" |
| 统计疑 | "重建 index（全量）" |

### 1.2 已内置规则，不必反复写

- `raw/` 只读、`log.md` append-only、`index.md` 六变量同步、双入口 SHA-256、媒体通道顺序探测——Skill 自动执行；
- 只需补充：只读边界、追加位置、媒体读取范围（如 `--no-video`）、特殊输出要求。

### 1.3 文档预处理与媒体理解分工

- 确定性解析（PDF/DOCX/PPTX/XLSX 文本抽取、manifest 建立）走项目 `.venv` 固定脚本；
- 图片/视频理解走媒体通道顺序探测（图片：`Read` → 视觉 MCP；视频：`Read` → 视觉 MCP `analyze_video`），大批量按波次派只读 subagent。

## 二、基础命令速查

| 命令 | 说明 |
|---|---|
| `/obsidian-llm-wiki ingest <来源>` | 新资料入库 |
| `/obsidian-llm-wiki enhance-wiki-content <页面.md> [raw目录]` | 正文不动、末尾追加六节（最高频写命令） |
| `/obsidian-llm-wiki optimize <页面.md>` | 优化结构表达（不删媒体嵌入） |
| `/obsidian-llm-wiki query <问题>` | 只读问答 |
| `/obsidian-llm-wiki lint` | 健康检查（只校验不修） |
| `/obsidian-llm-wiki index` | 全量重建索引 |
| `/obsidian-llm-wiki update-raw-reference <页面.md> <raw目录>` | 媒体引用一站式改写全路径 |
| `/obsidian-llm-wiki sync` | 合并 defer 队列片段（共享文件唯一写者） |
| `/obsidian-llm-wiki log <mode>` | `status` / `query` / `rotate now\|year\|size\|auto` |

## 三、高频模板

### 3.1 普通目录入库

```text
/obsidian-llm-wiki ingest raw/AI/<资料名>/
```

自动：建 manifest → 媒体通道探测 → 建页 → 六节 → index/log 收尾。

### 3.2 截图课程入库（大批量波次）

```text
/obsidian-llm-wiki ingest raw/AI/<截图课程目录>/
图片超过 10 张按波次派只读 subagent，逐张九字段返回，批次末尾按 manifest 对账。
```

### 3.3 内容增强两形态

```text
/obsidian-llm-wiki enhance-wiki-content wiki/AI/<页面>.md raw/AI/<资料名>/   # 形态 A：带 raw，媒体分析
/obsidian-llm-wiki enhance-wiki-content wiki/AI/<页面>.md                    # 形态 B：仅页面文字提炼
```

### 3.4 带视频的页面增强 / 显式跳过视频

```text
/obsidian-llm-wiki enhance-wiki-content wiki/AI/<页面>.md raw/AI/<资料名>/             # 视频默认自动探测读取
/obsidian-llm-wiki enhance-wiki-content --no-video wiki/AI/<页面>.md raw/AI/<资料名>/  # 跳过视频，标注视觉未识别
```

视频默认随 manifest 自动探测（`Read` 最小代表视频试读 → `analyze_video` 兜底 → 降级标注）；单文件超限或视觉通道均不可用时优先运行时视频工具抽帧/转写，都不可用才标"视频视觉未识别"记未决项。

### 3.5 媒体引用修复

```text
/obsidian-llm-wiki update-raw-reference wiki/AI/<页面>.md raw/AI/<新目录>/
```

仅当目标文件真实存在才改写为 `![[raw/<目录>/<文件名>]]`；frontmatter 与索引缺才补、有则只验证。

### 3.6 只读问答

```text
问：<问题>。只读，不改任何文件，回答标注 [[来源页面]]。
```

### 3.7 lint / index / 补录

```text
/obsidian-llm-wiki lint                 # 只报告不修复
/obsidian-llm-wiki index                # 全量重建（增量修不动时）
/obsidian-llm-wiki optimize wiki/AI/<页面>.md   # 补录既有页面走写命令
```

### 3.8 migrate 迁移

```text
/obsidian-llm-wiki migrate   # 先只读规划，与用户逐目录确认后再执行
```

### 3.9 归档 / 去索引 / 删除（谨慎）

```text
把 wiki/AI/<页面>.md 从 index 移除但保留文件      # 去索引
/obsidian-llm-wiki delete wiki/AI/<页面>.md       # 物理删除（逐个显式，禁递归/通配符）
```

### 3.10 log 工作流

```text
/obsidian-llm-wiki log status
/obsidian-llm-wiki log query "<关键词>"
/obsidian-llm-wiki log rotate auto
```

### 3.11 批量 defer + sync（多任务/多会话并行首选）

```text
/obsidian-llm-wiki enhance-wiki-content --defer wiki/AI/<页面1>.md raw/AI/<资料1>/
/obsidian-llm-wiki enhance-wiki-content --defer --no-video wiki/AI/<页面2>.md raw/AI/<资料2>/
/obsidian-llm-wiki sync --dry-run    # 批次末尾先校验
/obsidian-llm-wiki sync              # 一次合并 index/log，共享文件唯一写者
```

## 四、命令决策树

```text
需求是什么？
├─ 有新资料 ──────────── ingest（批量并行带 --defer）
├─ 页面已有、要补提炼 ── enhance-wiki-content（带 raw=形态 A / 无 raw=形态 B）
├─ 页面要改写表达 ────── optimize
├─ 只想问 ────────────── query（只读）
├─ 引用断链/目录迁移 ── update-raw-reference
├─ 统计/结构存疑 ─────── lint → 必要时 index 全量重建
├─ 批量/多会话并行 ──── 各写命令 --defer → 收尾 sync
└─ 日志问题 ──────────── log status / query / rotate
```

## 五、最佳实践

1. 高频日常维护优先 `enhance-wiki-content`——正文零风险，只追加不改写；
2. 多任务批量处理一律 `--defer`，批次末尾一次 `sync`，避免并行会话互踩共享文件；
3. 媒体密集资料先看 manifest 对账结果再动笔，缺页/重名先报告不猜测；
4. 视频/图片看不清就如实标注"视觉未识别"，绝不依文件名编造内容；
5. 页脚统计永远按当次扫描值覆盖，不在旧值上递增；
6. 删除类操作逐个显式路径，先查入链再动手；
7. query 默认只读；要归档答案为新页面时再转写命令；
8. schema 变更一次同步双入口并验 SHA-256。

## 六、常见避坑

1. 不要在建 manifest 时就把视频预判为"无法识别"——必须先探测（`Read` 试读最小视频）再下结论；
2. 不要用 `wiki_file_count` 顶替 `indexed_page_count` 填统计行——两者必须独立验证；
3. 不要为追加日志而整读大 `log.md`——用 EOF 直追 + 有界验证；
4. 不要在 index 表格里一行放两个 `[[链接]]`——一行 = 一个页面；
5. 不要在优化页面时顺手删除或重排已有嵌入——顺序是权威顺序；
6. 不要把真实资料内容、密钥或本地绝对路径带进公开仓库——范例与分享一律脱敏。

## 相关资源

- Karpathy, [llm-wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) —— 方法论源头
- Skill 主文件 `SKILL.md` —— 命令定义、媒体通道探测、六变量口径、defer/sync 完整 SOP
- `references/schema.md` —— schema 通用模板
- `references/defer-sync.md` —— 延后同步完整 SOP
- `references/log-rotation.md` —— 日志分卷流程
- `references/exam-collection-playbook.md` —— 题库截图流手写合集页专用 playbook
