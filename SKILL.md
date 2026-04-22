---
name: obsidian-llm-wiki
description: "LLM Wiki 模式：用 LLM 持续维护 Obsidian 知识库。支持 ingest（摄入新资料）、query（查询知识）、lint（健康检查）、migrate（迁移）、index（重建索引）。适用于已配置 CLAUDE.md 模式的 Obsidian vault，或需要初始化 LLM Wiki 模式的新 vault。当用户提到 wiki、知识库维护、ingest、知识管理、Obsidian 笔记整理时触发。"
---

# Obsidian LLM Wiki Skill

用 LLM 持续维护 Obsidian 知识库。基于 raw/wiki/schema 三层架构。

## 前置条件

使用前，项目根目录必须有 `CLAUDE.md`（模式定义文件）。如果不存在，引导用户初始化：

1. 询问用户的知识库有哪些领域（如"读书笔记"、"AI"、"投资"）
2. 使用 [references/schema.md](references/schema.md) 作为模板，生成项目专属的 `CLAUDE.md`
3. 创建 `raw/` 和 `wiki/` 目录结构
4. 创建空的 `index.md` 和 `log.md`

## 模板

本 Skill 自带通用模板，位于 `assets/` 目录：
- `assets/wiki-page.md` — 通用 wiki 页面
- `assets/book-note.md` — 读书笔记
- `assets/meeting-note.md` — 会议记录
- `assets/tool-page.md` — 工具页面

**优先级：** 如果项目根目录有 `templates/` 目录，优先使用项目模板；否则使用 Skill 自带的 `assets/` 模板。

模板中的 `{{domain}}`、`{{date}}`、`{{title}}` 等占位符由 Claude 根据项目 CLAUDE.md 的配置填写。

## 命令

### /obsidian-llm-wiki ingest <source>

处理 raw/ 中的新来源，集成到 wiki。

步骤：
1. 确认来源文件在 `raw/` 对应目录中
2. 读取来源文件（PDF 使用 Read tool 的 pages 参数）
3. 与用户讨论关键要点
4. 在 `wiki/` 对应目录创建摘要页面：
   - 读取项目 CLAUDE.md 确定领域和路径映射
   - 选择合适的模板（从项目 templates/ 或 Skill assets/）
   - 添加 YAML frontmatter（根据 CLAUDE.md 中的规范）
   - 添加 inline tags（与 frontmatter 匹配）
   - 包含一句话摘要
   - 添加「相关」和「来源」部分
5. 更新与新内容相关的已有 wiki 页面
6. 更新 `index.md`
7. 追加条目到 `log.md`，格式：`## [YYYY-MM-DD] ingest | <标题>`

### /obsidian-llm-wiki query <问题>

使用 wiki 回答问题。

步骤：
1. 读取项目 `CLAUDE.md` 了解架构
2. 读取 `index.md` 了解可用内容
3. 从索引定位相关 wiki 页面
4. 读取相关页面
5. 综合答案，引用页面 `[[标题]]`
6. 询问用户是否将答案归档为新 wiki 页面
7. 如果是，创建页面并更新 index.md 和 log.md

### /obsidian-llm-wiki lint

健康检查 wiki。

步骤：
1. 读取 `index.md`，验证每个列出的页面存在
2. 读取每个 wiki 页面，检查：
   - YAML frontmatter 存在且格式正确
   - frontmatter 中的 tags 与 inline tags 一致
   - 页面至少有 2 个出站 wiki 链接
   - 无断裂的 wiki 链接（链接到不存在的页面）
   - 同主题页面间无矛盾
3. 找出孤立页面（无其他页面的入链）
4. 找出值得拥有独立页面的内联提及
5. 检查过期内容（30+ 天未更新）
6. 向用户报告发现
7. 追加 lint 报告到 `log.md`

### /obsidian-llm-wiki migrate

一次性迁移助手。用于将已有的 Obsidian 笔记迁移到 LLM Wiki 模式。

步骤：
1. 扫描项目目录，找出不在 raw/ 和 wiki/ 中的 .md 文件
2. 与用户确认每个文件属于哪个领域
3. 对每个文件：
   a. 读取文件内容
   b. 提取 inline tags
   c. 生成 YAML frontmatter（根据 CLAUDE.md 规范）
   d. 确定目标：raw/（源资料）或 wiki/（知识页面）
   e. 写入新位置
   f. 记录迁移日志
4. 所有文件迁移完成后，重建 index.md

### /obsidian-llm-wiki index

从当前 wiki 状态重建 index.md。

步骤：
1. 扫描 wiki/ 目录下所有 .md 文件
2. 对每个文件，读取 frontmatter 和第一行内容
3. 按领域组织
4. 写入新的 index.md

## 守则

- 绝不修改 `raw/` 下的文件
- 覆盖已有 wiki 内容前须确认
- log.md 条目 append-only
- 保持中文内容
- 不确定时询问用户
- 所有路径和领域从项目 CLAUDE.md 读取，不硬编码
