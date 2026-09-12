# 延后同步（defer）与队列合并（sync）SOP

批量维护或多运行时（如 ZCode 与 Codex 同时维护同一 vault）并行时，每个写命令收尾都要改 `index.md`、跑精校、同步三处页脚、再追加 `log.md`——共享文件操作把并行会话串行化并互踩（锚点漂移、页脚覆盖、modified-since-read）。本机制把共享文件从「每任务必写」降级为「批次末尾一次合并」：

- **阶段一（defer）**：写命令带 `--defer` 参数，任务只写自己的页面 + 一个专属队列片段，完全不触碰 `index.md` / `log.md`；
- **阶段二（sync）**：批次结束后由任一空闲会话运行 `/obsidian-llm-wiki sync`，作为共享文件**唯一写者**一次性合并。

## 1. 队列片段规范

- 位置：`<vault>/logs/queue/`（不属于 `wiki/`，不计入 `index.md` 页面统计）。
- 文件名：`<YYYYMMDD-HHMMSS>-<4位随机>-<动作>-<页面短名>.md`（时间戳 + 随机后缀保证跨会话/跨运行时唯一；页面短名超长可截断）。
- 模板：[assets/queue-fragment.md](../assets/queue-fragment.md)。片段由三部分组成：
  - **元信息**（HTML 注释 `key: value`）：`task`（命令名）、`date`（与 log 条目日期一致）、`page`（vault 相对路径，必须以 `wiki/` 开头）、`section`（目标分区标题 `## 领域 / 子分区`）、`summary`（顶部维护块动作摘要）；
  - **index 条目**（`<!-- index-entry -->` 围栏）：现成的三列数据行 `| [[页面标题]] | 一句话摘要 | 标签 |`，按 §Index 章节与表格规范书写——任务当下写好，摘要质量与增量模式一致；
  - **log 条目**（`<!-- log-entry -->` 围栏）：现成的最终记录全文（`## [YYYY-MM-DD] 动作 | 标题` + 标准紧凑字段）。「维护」字段固定注明：`index/log 同步延后（defer），六变量以批次 /sync 精校为准`。
- 最小合法性（`scripts/flush_queue.py` 逐项校验）：含队列标记 `obsidian-llm-wiki queue v1`、两个围栏齐全、log 条目有 `## [` 标题、`date` 与标题日期一致、`page` 存在且位于 `wiki/` 下。
- 同日同页同动作会产生相同条目标题——写片段时在标题中加区分词，避免合并时被去重跳过。

## 2. defer 模式任务收尾 SOP

写命令（ingest / optimize / enhance-wiki-content / update-raw-reference / extract-thinking-frameworks / migrate / delete）带 `--defer` 时（参数紧跟命令名，位置参数原样保留）：

1. 页面级工作**照常全部完成**：frontmatter、正文、图片嵌入、sources、交叉引用、页面级验证、raw 只读红线等一律不变。
2. 按模板构造队列片段：index 条目行 + log 条目全文都在任务当下写好（此时上下文最新鲜）。
3. 用唯一文件名写入 `logs/queue/`；**不做** index.md 编辑、六变量精校、三处页脚同步、log-preflight 预检、log.md 追加。
4. 汇报：片段路径 + 「已入队待 /sync 合并」清单。片段写完即视为任务收尾（defer 分支的完成标准）。
5. `delete --defer` 的片段照常写（index 条目围栏留空说明、log 条目记录删除动作）；条目移除由 `/sync` 执行。

> defer 期间 index 统计滞后是**正常态**：以最近一次 `/sync` 后的页脚为准；lint / query 照常报告缺口，但不把队列中已有片段的页面当「待补录」处理。

## 3. /sync 执行 SOP（共享文件唯一写者）

`/obsidian-llm-wiki sync`（无位置参数）与 `/obsidian-llm-wiki sync --dry-run`（只列出片段与校验结果，零写入）。执行顺序：

1. **前置确认**：无其他会话正在运行 `/sync`（锁兜底，见下）。
2. **列表与校验**：运行固定脚本 `scripts/flush_queue.py --vault-root <vault> --dry-run` 得片段清单（merged / skipped_duplicate / dropped_missing_page / invalid）。零片段 → 空队列收敛：按需刷新页脚统计即可（幂等），不取锁。
3. **index 条目合并**（agent 执行，逐片段）：
   - 按 `section` 定位分区章节；**同名分区存在多处时报告并按现有章节顺序判断归属**（不确定则放入第一处并报告）；
   - 分区不存在时按 §Index 章节与表格规范新建（表头 `| 页面 | 摘要 | 标签 |` + 分隔行，位置遵循现有章节排序约定）；
   - 页面已有条目（按 `[[页面标题]]` 查重）→ 跳过插入；
   - `delete` 片段 → 移除对应数据行；
   - 插入/移除后不单独跑精校——留到下一步统一做。
4. **统一精校 + 三处页脚同步**：运行 `references/index_stat.py` 得六变量终值 → 顶部维护块（`<summary>` 或 `同步索引：队列合并 N 条（页面A、页面B…）`）+ 底部统计行 + 索引健康行**同一次编辑**，三处日期字面一致 → 重跑精校确认 `footer_match=true`（并行漂移则按最终扫描值二次覆盖）。
5. **log 合并**：把全部片段 log 条目 + `/sync` 自身最终记录合并为待追加文本，跑一次 `log-preflight.ps1`（`rotation_due=true` 先按 log-rotation.md 轮转）；随后运行 `scripts/flush_queue.py --vault-root <vault>`（无 `--dry-run`）完成按序追加、完整性验证（前缀 SHA-256 零改动 + 字节增量对账 + 标题全库唯一）与已合并片段单文件清理。
6. **收尾**：`/sync` 自身最终 log 记录（标题建议 `sync | 队列合并 N 条：…`）由 agent 按常规 EOF 直追方式追加并验证；输出六变量 + 合并/跳过/丢弃清单。

**锁**：脚本取锁 `logs/queue/.sync.lock`（`O_CREAT|O_EXCL`，写 PID + 时间）。已存在且 <15 分钟（`--lock-minutes`）→ 退出码 3 终止，提示稍后重试；过期视为死锁残留，单文件删除后重取。空队列运行不取锁、零写入。

**脚本退出码**：`0` 成功（含空队列/无可合并项）；`2` 用法或路径错误；`3` 锁被占用；`5` 追加后验证失败（片段保留，修复后重跑——按条目标题去重，幂等）。

## 4. 异常处理

| 情形 | 处置 |
|---|---|
| 锁被占用（<15 分钟） | 终止并提示；确认另一会话完成后重试 |
| 过期锁 | 脚本自动单文件删除后重取，报告中注明 |
| 片段非法（缺围栏/标记/日期不一致等） | 保留片段，报告中列 `invalid` 与具体错误；agent 修复片段后重跑脚本 |
| 目标页面缺失 | 保留片段，报告中列 `dropped_missing_page`；agent 核实（页面被改名/删除）后修正 `page` 元信息重跑，或经用户确认后单文件删除片段 |
| 条目已存在（标题重复） | `skipped_duplicate`，成功后脚本随已合并片段一并单文件清理 |
| 分区不存在 / 同名分区多处 | agent 按 §Index 章节与表格规范处理并报告（见 SOP 第 3 步） |
| 追加验证失败（退出码 5） | 片段保留；排查后直接重跑（标题去重保证幂等，不会重复追加） |
| log-preflight 判定轮转 | 先按 log-rotation.md 完成轮转，再重跑合并 |
| 合并期间并行新投放 | 遵循 §并行会话干扰防护：页脚按最终扫描值覆盖；新页面只报告不代补 |

## 5. 多运行时并行（ZCode / Codex 同时维护）

- defer 与 sync 全部基于「文件约定 + 标准库脚本」，与运行时无关；Codex 走其既有 PowerShell 通道，ZCode 走 Git Bash 通道。
- 页面级并行零协调：各会话只写自己的页面与自己的片段文件（文件名含时间戳 + 随机后缀）。
- 约定：批次结束后由**任一空闲会话**跑一次 `/sync`；锁文件兜底双合并；两个会话不得刻意同时运行 `/sync`。

## 6. 与既有章节的关系

- §强制维护遍历：defer 任务第 4 步（index）与第 6 步（log）延后为写片段，其余步骤照常。
- §写命令的标准操作流程：`--defer` 分支跳过第 3–6、8 步，改为写片段。
- §增量 vs 全量分工：`/sync` 为**队列合并**模式，是增量（逐任务）与全量（`/index`）之外的第三条路径。
- §并行会话干扰防护：defer 是首选隔离模式；防护规则适用于非 defer 任务与 `/sync` 执行过程。
- `logs/queue/` 不计入 `index.md` 页面统计；已合并片段即删，队列目录不承载长期内容。
