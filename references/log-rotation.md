# 日志分卷与轮转（Log Rotation）

仅在显式 `log` 工作流或 `scripts/log-preflight.ps1` 报告 `rotation_due=true` 时使用本参考。

## 接口

- `log status`：以 `-Detailed -Json` 运行预检脚本；只读，绝不轮转。
- `log query "<条件>"`：用 `rg` 检索 `log.md` 与 `logs/archive/*.md`，只读取命中处有界上下文。
- `log rotate now`：不问日期与大小，立即轮转。
- `log rotate year`：仅当活动日志首条目早于当前日历年时轮转。
- `log rotate size`：仅当投影字节数达到配置阈值时轮转。
- `log rotate auto`：年份或大小任一到期即轮转。

query、只读 lint/audit、`log status`、`log query` 与无文件变化的任务永不自动轮转。写任务在追加唯一最终日志条目前，把完整待追加文本（含所有分隔换行与末尾换行）传给预检脚本。

## 标准条目

保持既有标题契约：

```markdown
## [YYYY-MM-DD] <action> | <title>

- 范围：本次任务及边界。
- 变更：涉及的文件和操作。
- 资料：来源、图片或附件核对结果。
- 维护：frontmatter=<valid/repaired/n-a>；index=<unchanged/refreshed>；schema=<unchanged/updated, hash-equal>；raw=unchanged。
- 验证：实际执行的检查及结果。
- 未决：存在异常时填写。
```

`范围`、`变更`、`维护`、`验证` 为必需字段；`资料` 仅在涉及来源或媒体时填写；`未决` 仅在存在未解决问题时填写。`index.md` 变化时，在 `维护` 中记录六个索引变量。不得为迁就新格式改写旧条目。

## 分卷目录结构

```text
log.md
logs/
|-- log-archives.md
`-- archive/
    `-- log-YYYY-MM-DD-to-YYYY-MM-DD.md
```

`log.md` 是唯一活动日志。`logs/archive/` 下文件不可变。`logs/` 在 `wiki/` 之外，永不计入 `index.md` 页面统计。目录与文件名使用 ASCII 英文字符。

仅在首次真实轮转时创建 `logs/log-archives.md`：

```markdown
# Log Archives

> 历史日志分卷清单。归档文件只读，不得修改或继续追加。

| Archive | Period | Entries | Bytes | SHA-256 | Trigger | Archived |
|---|---|---:|---:|---|---|---|
```

每次成功轮转追加一行；绝不重写或重排既有行。

## 轮转流程

1. 先完成任务并生成它的唯一完整最终日志条目，再轮转；操作前立即重跑预检。
2. 只读取确定首、末 `## [YYYY-MM-DD]` 标题所需的元数据与有界内容；统计标题数时不把日志正文回传模型上下文（如 `grep -c '^## \['` 计数、`grep -m1` 取首末标题）。
3. 记录活动日志的精确字节长度、条目数、最后写入时间与 SHA-256；目标归档文件已存在则立即停止。
4. 用核实过的日期范围命名 `logs/archive/log-YYYY-MM-DD-to-YYYY-MM-DD.md`；仅在首次真实轮转时创建 `logs/` 与 `logs/archive/`。
5. 用精确字面路径整文件移动活动日志：Git Bash 用 `mv "<字面路径>" "<字面路径>"`，原生 PowerShell 用 `Move-Item -LiteralPath`。绝不"复制后清空"、剪切条目、重写历史、使用通配符或覆盖目标。
6. 要求归档后的字节长度、条目数与 SHA-256 和移动前完全一致。
7. 从 `assets/log-active.md` 创建新 `log.md`；不复制旧条目、摘要或尾部内容。
8. 创建或追加 `logs/log-archives.md` 一行：归档路径、时间范围、条目数、字节数、完整 SHA-256、触发方式、归档日期。
9. 写任务内的自动轮转：把该任务的单条最终条目追加到新日志并在其中包含归档事实，不另写第二条 `rotate` 条目；显式轮转任务则追加一条标准 `rotate` 条目。
10. 校验新日志格式、归档清单行、末尾换行、任务标题唯一、归档文件哈希未变。

移动前检测到元数据或哈希并发变化时，废弃方案并重新推导。轮转失败但原 `log.md` 完整时，把任务条目追加到原日志并标注"轮转待处理"。移动成功但新日志创建失败时，仅当目标路径不存在且归档仍与记录的长度和哈希一致，才把归档恢复为 `log.md`；否则停止并报告确切状态，绝不覆盖任一路径。

## 低 Token 追加准备（Claude Code / Git Bash）

普通追加前，内部检查 `tail -n 80`（必要时扩到至多 `tail -n 200`），只回传：

- 原字节数（`wc -c`）、SHA-256（`sha256sum`）与最后写入时间；
- 精确任务标题是否已存在于有界尾部（对尾部文本 `grep -F -c "<完整标题行>"`；已存在则不重复追加）；
- 用作 Edit 锚点或复查的末尾唯一 2–4 行。

不把完整尾部回传模型上下文。追加后只回传：唯一标题计数、长度增量、原前缀哈希结果、末尾换行结果、新条目是否为最后一条。

- 写入机制按 SKILL.md「log.md 追加（大文件安全）」执行：首选 heredoc `cat >> "<log.md>" <<'LOGEOF'`，次选 `Edit + tail 锚点`；禁止为追加而整读文件。
- 原前缀哈希验证：`head -c <原字节数> "<log.md>" | sha256sum` 必须等于追加前整文件 SHA-256，证明既有字节未被改动。

## 备份边界

轮转是组织行为，不是独立备份。绝不自动删除、压缩、合并或继续追加历史分卷。真正的备份必须存放在独立管理的备份位置。
