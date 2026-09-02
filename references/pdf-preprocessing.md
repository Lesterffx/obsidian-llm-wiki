# PDF 预处理协议（pdf-preprocessing.md）

本 reference 只规定 PDF 的文本、页码、元数据、图片对象与视觉降级流程。
临时文件清理由独立的 [temp-cleanup.md](temp-cleanup.md) 负责；不要把两个工作流合并。

## 固定入口

PDF 预处理使用 Skill 自带固定脚本，不为普通 PDF 任务临时生成另一份预处理脚本。
解释器用知识库项目虚拟环境（`.venv/Scripts/python.exe`），Git Bash 调用格式：

```bash
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 \
  "<vault-root>/.venv/Scripts/python.exe" \
  "<skill_base>/scripts/preprocess_pdf.py" \
  --input "<PDF 绝对路径>" \
  --vault-root "<知识库绝对路径>" \
  --task-id "<时间戳-安全任务标识>"
```

其中 `<skill_base>` 即本 Skill 的安装根目录（随运行时不同，如 ZCode 为 `~/.zcode/skills/obsidian-llm-wiki`、Claude Code 为 `~/.claude/skills/obsidian-llm-wiki`）。约束：

- `task-id` 只能包含字母、数字、点、下划线和连字符，且不能是 `.` 或 `..`。
- 输出目录固定为 `<vault-root>/tmp/obsidian-llm-wiki/<task-id>/`。
- 任务目录必须在运行前不存在；脚本拒绝覆盖或复用既有目录。
- 脚本只读取输入 PDF，不修改 `raw/`，也不写入 `wiki/`、`index.md`、`log.md` 或 Schema。
- 中间产物只进入任务目录，不落在 `raw/` 或 vault 其他位置。

## 提取器分工

- `pypdf` 优先负责中文文本与 PDF 元数据。
- PyMuPDF 负责页数、页面尺寸、嵌入图片对象、xref、图片尺寸与必要的整页渲染。
- 不要把 PyMuPDF 的文本结果默认当作中文正文。它只在 pypdf 质量不合格且自身质量更高时作为逐页降级结果。
- 不要因为终端显示乱码就判断文件损坏；先确保 UTF-8 环境（`PYTHONUTF8=1`），再检查脚本输出的逐页质量指标。

## 乱码与质量判定

脚本对每页分别计算替换字符比例、控制字符比例与连续替换字符，并按以下顺序决策：

1. `pypdf` 有文本且未超过异常阈值时，选用 `pypdf`（状态 `ok`）。
2. `pypdf` 不合格时比较 PyMuPDF；只有 PyMuPDF 通过阈值且质量更高时才选用它（状态 `fallback`）。
3. 两者文本都为空时，状态为 `empty_text`。
4. 两者都疑似乱码时，状态为 `corrupt_text`。
5. `empty_text` 和 `corrupt_text` 页面自动渲染为 PNG（`rendered_pages/page-NNN.png`），页面正文位置只写「需视觉读取」，不得把乱码写入 Wiki。

质量检测是风险筛选，不替代内容核对。

## 视觉读取衔接

`requires_visual` 页面与提取图片的视觉理解，按 SKILL.md「运行时与网关适配」的三级通道执行：
先试 `Read` 直读；不可用时用视觉理解 MCP（如智谱 `zai-mcp-server`，`analyze_image` / `extract_text_from_screenshot` 等，`image_source` 传本地绝对路径）；仍不可用才标记「视觉未识别」降级。
不假设 Tesseract、OpenCV、PaddleOCR、RapidOCR 等传统 OCR 引擎可用。

## 固定产物

全部位于 `<vault-root>/tmp/obsidian-llm-wiki/<task-id>/`：

| 文件/目录 | 内容 |
|---|---|
| `metadata.json` | 来源路径、SHA-256、页数、双提取器元数据、`text_priority`、`visual_pages` |
| `pages.json` | 逐页状态、选中提取器、质量指标、文本、图片出现数 |
| `page_text.md` | 按页分节正文；异常页只有「需视觉读取」占位 |
| `image_manifest.csv` | 图片出现级清单（页码、occurrence、xref、尺寸） |
| `unique_image_manifest.csv` | xref 去重图片清单（含 pages、occurrence_count、sha256） |
| `images/` | 唯一嵌入图片（`xref-<xref>.<ext>`） |
| `rendered_pages/` | 仅异常页整页渲染 PNG |
| `created_files.json` | 本次创建的普通文件清单、建议清理顺序、`created_directories`、容器与保护路径标注 |

`created_files.json` 关键字段：

- `cleanup_order`（与 `created_files` 相同）：建议清理顺序，清单自身排在最后一位；
- `created_directories`：本次创建的目录，按最深优先排序；
- `conditional_cleanup_directory`：即 `<vault-root>/tmp/obsidian-llm-wiki/`，单独标注、条件删除；
- `protected_tmp_root`：即 `<vault-root>/tmp/`，永不删除；
- `workflow_root_created_by_task`：本次运行是否新建了工作容器。

脚本标准输出返回一行 JSON 摘要（`task_root`、`pages`、`text_chars`、`visual_pages`、`image_occurrences`、`unique_images`、`created_files`）。后续图片分析必须按 manifest 索引对账；不得依赖文件系统返回顺序。

## 使用边界

- 完成页面、索引和必要验证后，再进入独立的临时文件清理流程（[temp-cleanup.md](temp-cleanup.md)）。
- 中断恢复时只能继续处理已知 task-id 和它的登记清单，不能遍历同级历史目录。
