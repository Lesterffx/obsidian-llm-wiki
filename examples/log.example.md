> 本文件是 `log.md` 范例：使用时从下方分隔线之后复制到 vault 根目录重命名为 `log.md`（首个真实条目即 init 记录）。`log.md` 是 append-only 操作日志——只追加，不删除、不改写已有条目；历史分卷入口为 `logs/log-archives.md`（首次真实轮转时创建）。

---

## [YYYY-MM-DD] init | 初始化知识库

- 范围：vault 根目录；创建三层架构初始文件
- 变更：新建 `raw/`、`wiki/` 目录与占位领域子目录；`AGENTS.md` / `CLAUDE.md`（双入口，SHA-256 一致）；空 `index.md`、本 `log.md`
- 维护：frontmatter=n-a（尚无 wiki 页面）；index=created（0 条目，页脚占位符待首次写命令刷新）；schema=created, hash-equal；raw=unchanged
- 验证：目录与文件存在性检查通过；schema 双入口 sha256sum 相等；`index.md` 以换行结束

## [YYYY-MM-DD] <action> | <标题>

- 范围：<任务作用域：目录/页面/命令>
- 变更：<新增/修改/移动的文件清单；删除必须来自用户明确授权>
- 维护：frontmatter=<valid/repaired/n-a>；index=<unchanged/refreshed/补录 N 条>；schema=<unchanged/updated, hash-equal>；raw=unchanged
- 验证：<实际执行的检查与结果：六变量与页脚复验 footer_match、嵌入对账、SHA-256 等>
- 资料：<仅在涉及来源、图片、视频或附件时记录>
- 未决：<仅在存在异常、缺失或待处理事项时记录>

## 追加与分卷规则（范例附注，复制真实 log.md 时删除本节）

- 新条目永远追加在文件末尾（EOF 直追：bash heredoc `cat >> log.md <<'LOGEOF'` / PowerShell `Add-Content -LiteralPath`）；同一任务只追加一条最终记录，不为中间步骤重复写日志。
- 追加前跑 Skill 固定只读预检 `scripts/log-preflight.ps1`（默认阈值 2 MiB；投影超阈值或活动日志跨年 → `rotation_due=true`）。Git Bash 多行中文文本走 `-PendingAppendB64` Base64 通道；原生 PowerShell 可传 `-PendingAppend` 明文参数。脚本只读：不创建/修改/移动/删除文件、不写临时文件。
- 追加后四项验证：字节增量 == 待追加文本 UTF-8 字节数；精确任务标题在有界尾部恰好出现 1 次且为最后一条；文件仍以换行结束；`head -c <原长度> log.md | sha256sum` == 追加前整文件 SHA-256。任一项不满足即如实报告失败。
- 达到 2 MiB 或跨年时**整文件移动**轮转到 `logs/archive/log-<起始日>-至-<截止日>.md`，绝不"复制后清空"、拆分或改写历史；新活动日志从 Skill `assets/log-active.md` 模板创建；`logs/` 不计入 `index.md` 页面统计；轮转是组织行为，不是备份，历史分卷永不自动删除或合并。
