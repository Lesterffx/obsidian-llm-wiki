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
- **Schema (CLAUDE.md)** — 告诉 LLM wiki 的结构、约定、工作流的配置文件。这是让 LLM 成为有纪律的 wiki 维护者而非通用聊天机器人的关键。你和 LLM 随着时间推移共同演化这个文件。

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
- **CLAUDE.md** —— 每个 Obsidian vault 根目录必须有此配置文件。如果不存在，Skill 会引导你初始化

## 限制条件

- 绝不修改 `raw/` 下的文件（不可变层）
- 覆盖已有 wiki 内容前须用户确认
- `log.md` 条目 append-only，不删除已有条目
- 保持中文为主要内容语言
- 不破坏已有 wiki 链接
- 编辑 wiki 页面时绝不删除已有图片引用，编辑前后须校验图片引用完整性
- 所有路径和领域从项目 CLAUDE.md 读取，不硬编码

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
│   └── tool-page.md      # 工具页面
└── references/
    └── schema.md         # CLAUDE.md 通用模板（供新项目初始化）
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
| `/obsidian-llm-wiki lint` | 健康检查：矛盾、孤立页面、缺失引用、过期内容 |
| `/obsidian-llm-wiki migrate` | 一次性迁移：将已有笔记迁移到 LLM Wiki 模式 |
| `/obsidian-llm-wiki index` | 从当前 wiki 状态重建 index.md |

## SKILL.md 关键内容

SKILL.md 是 Skill 的核心配置，定义了：

1. **前置条件检查** —— 如果项目缺少 CLAUDE.md，引导用户初始化（询问领域 → 生成 CLAUDE.md → 创建目录结构）
2. **模板优先级** —— 项目 `templates/` 目录 > Skill `assets/` 目录。模板中 `{{domain}}`、`{{date}}` 等占位符由 Claude 根据项目 CLAUDE.md 填写
3. **页面规范** —— 每个 wiki 页面必须包含 YAML frontmatter（title、created、updated、domain、tags、sources、status）、inline tags、一句话摘要、正文、相关链接、来源引用
4. **工作流守则** —— raw/ 只读、覆盖前确认、日志 append-only、从 CLAUDE.md 读取配置而非硬编码

## 快速开始

### 1. 确认 Skill 可用

在任意目录下启动 Claude Code，输入 `/obsidian-llm-wiki`，确认 Skill 被识别。

### 2. 初始化新 Obsidian 仓库

在 Claude Code 中 `cd` 到你的 Obsidian vault 目录，运行 `/obsidian-llm-wiki`。如果缺少 CLAUDE.md，Skill 会引导你：

1. 告知你的知识库有哪些领域（如"读书笔记"、"AI"、"投资"）
2. 使用 `references/schema.md` 模板生成项目专属的 CLAUDE.md
3. 创建 `raw/` 和 `wiki/` 目录结构
4. 创建空的 `index.md` 和 `log.md`

### 3. 开始使用

- 将原始资料放入 `raw/<领域>/` 对应目录
- 运行 `/obsidian-llm-wiki ingest` 处理新资料
- 运行 `/obsidian-llm-wiki query` 查询知识
- 定期运行 `/obsidian-llm-wiki lint` 保持 wiki 健康

### 4. Obsidian 设置

在 Obsidian 设置中，将 `Settings → Files & Links → Attachment folder path` 设为 `raw`，确保新图片附件暂存在 raw/ 根目录，ingest 时按领域整理到对应子目录。
