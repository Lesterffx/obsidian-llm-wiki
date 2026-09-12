<!--
obsidian-llm-wiki defer 队列片段模板（--defer 任务专用）。
复制本文件内容到 <vault>/logs/queue/<YYYYMMDD-HHMMSS>-<4位随机>-<动作>-<页面短名>.md 并填占位符。
解析规则与完整 SOP 见 references/defer-sync.md；合并由 /obsidian-llm-wiki sync 执行。
-->
<!-- obsidian-llm-wiki queue v1 -->
<!-- task: <命令名，如 enhance-wiki-content / optimize / ingest / update-raw-reference> -->
<!-- date: <YYYY-MM-DD> -->
<!-- page: <wiki/…/页面.md，vault 相对路径，必须以 wiki/ 开头> -->
<!-- section: <## 领域 / 子分区> -->
<!-- summary: <顶部维护块动作摘要，如 同步索引：补录既有页面 <页面名>> -->

<!-- index-entry -->
| [[<页面标题>]] | <一句话摘要> | `#<标签1>` `#<标签2>` |
<!-- /index-entry -->

<!-- log-entry -->

## [<YYYY-MM-DD>] <操作> | <标题>

- 范围：…
- 变更：…
- 维护：frontmatter、标签与 sources 已检查；raw/ 未修改；Schema 双入口未改动；index/log 同步延后（defer），六变量以批次 /sync 精校为准。
- 验证：…
- 未决：…（如无可整行省略）
<!-- /log-entry -->
