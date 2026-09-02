# 临时文件与目录清理协议（temp-cleanup.md）

本 reference 规定 `tmp/obsidian-llm-wiki/` 任务产物的收尾清理。与 [pdf-preprocessing.md](pdf-preprocessing.md) 是两个独立工作流，不要合并执行。

## 权限边界

- 每次任务使用独立且运行前不存在的任务根目录：`<vault-root>/tmp/obsidian-llm-wiki/<task-id>/`。
- 清理权限只来自该次运行生成的 `created_files.json`，不能从「文件位于 tmp 下」推断可删除。
- 不扫描或清理同级其他任务目录，不清理历史遗留目录，不处理未登记文件。
- 永远不删除 `raw/`、`wiki/`、`index.md`、`log.md`、Schema、Skill 文件或任务根目录之外的任何文件。
- 普通目录仍禁止删除。唯一例外是本 reference 规定的本次任务空目录与空的 `tmp/obsidian-llm-wiki/` 工作容器。
- 始终保留 `<vault-root>/tmp/` 本身，不处理 `tmp/pdfs/` 等其他工作流或历史目录。

## 清理时机

- 页面、索引和必要验证完成后，在构建最终日志文字及最终回复前执行清理。
- 成功和可控失败都要进入清理阶段。
- 只有用户明确要求保留调试材料时才能跳过，并须列出保留路径。
- 中断后恢复时，只能继续处理已知 `task-id` 和对应登记清单，不能遍历同级目录寻找「可能属于本任务」的文件。

## 冻结清单

1. 读取 `created_files.json`，在删除前把完整清理顺序冻结在当前工作上下文。
2. `created_files.json` 自身必须是清理顺序中的最后一项。
3. 同时冻结 `created_directories`、`conditional_cleanup_directory` 和 `protected_tmp_root`；不得在清理过程中通过扫描发现新删除目标。
4. 对每个文件目标分别确认：
   - 登记在本次清单中；
   - 是普通文件，不是目录；
   - 解析后仍严格位于本次任务根目录；
   - 路径不含 `*` 或 `?`；
   - 不属于任何受保护路径。
5. 任一文件目标验证失败时，不删除该目标；继续处理其他已登记文件，但不得开始目录清理，并在最终结果中报告。

## 逐文件删除

每个文件必须使用一次独立命令。不得把多个路径放进一个命令，不得用循环、管道、通配符、`-Recurse`、`rm -rf` 或删除 Python。
Git Bash 单文件 `rm` 与 PowerShell 单路径非递归 `Remove-Item` 是等价首选（每个命令只碰一个明确路径）；若运行时配置了命令守卫，两种形态都应配置为对 tmp/temp 类目录内的单一路径免审批放行：

```bash
rm "<vault-root>/tmp/obsidian-llm-wiki/<task-id>/metadata.json"
```

等价备选（同一文件只删一次）：

```bash
powershell.exe -NoProfile -Command "Remove-Item -LiteralPath '<vault-root>/tmp/obsidian-llm-wiki/<task-id>/metadata.json'"
```

按清单顺序删除普通产物，最后单独删除 `created_files.json`。每条命令只对应一个明确文件；路径用正斜杠，含空格路径加引号。

## 逐目录删除窄例外

只有全部登记文件均已删除且任务根目录内普通文件数为 0，才能开始目录清理。

1. 按 `created_directories` 的既定顺序处理：最深层子目录在前，任务根目录最后。
2. 每个目录必须分别确认：
   - 路径来自 `created_directories`，或恰好等于 `conditional_cleanup_directory`；
   - 是目录且为空（`ls -A "<目录>"` 无任何输出）；
   - 路径不含 `*` 或 `?`；
   - 解析后位于本次任务根目录内，或恰好是 `<vault-root>/tmp/obsidian-llm-wiki/`；
   - 不等于 `protected_tmp_root`，也不位于 `tmp/pdfs/` 等其他工作流路径。
3. 每个空目录使用一次独立命令：

```bash
powershell.exe -NoProfile -Command "Remove-Item -LiteralPath '<vault-root>/tmp/obsidian-llm-wiki/<task-id>/images'"
```

4. 任务目录删除后，只读检查 `conditional_cleanup_directory`。仅当其中没有任何文件或目录时，才用另一条独立命令删除该工作容器。
5. 任一目录非空、校验失败或删除失败时，停止向上删除；不得改用 `-Recurse`、循环、管道或其他批量方式补救。
6. 递归与目录级删除命令（`rmdir`、`rm -r`/`rm -rf`、`Remove-Item -Recurse`）一律禁止使用；配置了命令守卫的运行时应保持对其直接拦截。若沙箱或审批策略拒绝目录删除，视为受控残留：不要换用其他等价方式绕过，保留空目录并报告具体阻断。
7. 严格保持单调用形态：powershell 单次调用、仅 `-LiteralPath`/`-Path` + 单一路径、无其他参数；任何附加参数都会回落审批或被拦截。

## 清理验证与结果报告

删除任务目录前，只读检查本次任务根目录：

```bash
find "<本次任务根目录>" -type f
```

- 返回普通文件数必须为 0。
- 不得因为验证发现其他任务目录仍有文件而扩大清理范围。
- 最终汇报六项：生成文件数、成功删除文件数、文件残留数、目录残留数、任务目录状态和工作容器状态。
- 最佳结果是 `<vault-root>/tmp/` 保留，而 `tmp/obsidian-llm-wiki/` 因为空而被删除。
- 文件或任务目录残留不为 0 时列出残留项，不得声称完整清理完成。
- 因策略阻断而仅剩空目录时，必须明确区分「文件已清空」和「目录删除未获执行许可」。
