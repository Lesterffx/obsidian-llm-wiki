#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""obsidian-llm-wiki 精校脚本：index.md 六变量统计验证（固定 reference 脚本）.

口径来源：SKILL.md §Index Metadata And Statistics（六变量计数口径 · 机检 · 精校）。

  - wiki_file_count         实际 wiki/**/*.md 文件数（排除 index.md / log.md / *.canvas / templates/ / assets/）
  - registered_domain_count schema『领域注册表』数据行数（CLAUDE.md 优先，AGENTS.md 对照）
  - indexed_page_count      index 数据行 [[title]] 可解析到唯一 wiki 文件、按 path 去重后的条目数
  - broken_count            无法唯一解析且不属于排除项的 index 链接（未命中 / 歧义）
  - missing_count           有 wiki 文件但无索引条目覆盖
  - duplicate_count         同一 wiki 页面重复出现的额外条目数（出现数 − 1）

排除项：.canvas / 图片 / 附件扩展名、raw/... 源链接、代码块与行内代码中的示例占位链接。

用法：
  python index_stat.py <vault_root> [--json]

示例（项目 .venv 优先，见 SKILL.md §文档预处理与运行环境）：
  .venv\\Scripts\\python.exe "<skill_base>/references/index_stat.py" "D:/path/to/vault"

输出：六变量 + 未收录/断链/重复明细 + 页脚旧值对照（漂移报告）。--json 输出机读结构。
退出码：0 = 正常完成（无论是否有缺口）；2 = 用法/路径错误。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):  # Windows 控制台默认 GBK，强制 UTF-8
    sys.stdout.reconfigure(encoding="utf-8")

# 排除项（Schema §Index 六变量计数口径 · 排除项）
ATTACH_EXT = (
    ".canvas", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".pdf",
    ".excalidraw", ".mp4", ".mov", ".mdx",
)
EXCLUDED_NAMES = {"index.md", "log.md"}
EXCLUDED_PARTS = {"templates", "assets"}

FOOT_STAT = re.compile(
    r"_统计：(\d+) 个已索引页面 \| (\d+) 个 Wiki 文件 \| (\d+) 个注册领域 "
    r"\| 上次更新于 (\d{4}-\d{2}-\d{2})_"
)
FOOT_HEALTH = re.compile(
    r"> 索引健康：未收录 (\d+) \| Markdown 断链 (\d+) \| 重复条目 (\d+)"
)


def scan_wiki(vault: Path) -> list[str]:
    """枚举 wiki/**/*.md（posix 相对路径），按口径排除非页面文件。"""
    files: list[str] = []
    wiki = vault / "wiki"
    if not wiki.is_dir():
        return files
    for p in sorted(wiki.rglob("*.md")):
        if p.name.lower() in EXCLUDED_NAMES:
            continue
        if any(part in EXCLUDED_PARTS for part in p.parts[:-1]):
            continue
        files.append(p.relative_to(vault).as_posix())
    return files


def count_registered_domains(vault: Path) -> tuple[int | None, list[str]]:
    """读 schema『领域注册表』数据行数；CLAUDE.md 优先，AGENTS.md 存在时对照行数。"""
    def table_rows(schema: Path) -> int | None:
        text = schema.read_text(encoding="utf-8")
        m = re.search(r"^#{1,3}\s*.*领域注册表.*$", text, flags=re.M)
        if not m:
            return None
        block: list[str] = []
        for line in text[m.end():].splitlines():
            if line.lstrip().startswith("|"):
                block.append(line.strip())
            elif block:
                break
        rows = [r for r in block[1:] if not re.fullmatch(r"\|[\s:|-]+\|?", r)]
        return len(rows)

    notes: list[str] = []
    primary = vault / "CLAUDE.md"
    secondary = vault / "AGENTS.md"
    count: int | None = None
    if primary.is_file():
        count = table_rows(primary)
        if count is None:
            notes.append("CLAUDE.md: 未找到『领域注册表』表格")
    if secondary.is_file():
        c2 = table_rows(secondary)
        if count is not None and c2 is not None and c2 != count:
            notes.append(f"双入口注册表行数不一致：CLAUDE.md={count}, AGENTS.md={c2}（须先同步再计数）")
        elif count is None and c2 is not None:
            count = c2
            notes.append(f"registered_domain_count 取自 AGENTS.md（{c2}）")
    if count is None and not notes:
        notes.append("vault 根未找到 CLAUDE.md / AGENTS.md 或其『领域注册表』")
    return count, notes


def extract_targets(vault: Path) -> list[str]:
    """抽取 index.md 全部 [[target]]（去 alias/锚点），剔除代码块与行内代码中的示例占位。"""
    index = vault / "index.md"
    text = index.read_text(encoding="utf-8")
    no_code = re.sub(r"```.*?```", "", text, flags=re.S)
    no_code = re.sub(r"`[^`\n]*`", "", no_code)
    targets: list[str] = []
    for t in re.findall(r"\[\[([^\]]+)\]\]", no_code):
        t = t.split("|")[0].split("#")[0].strip()
        if t:
            targets.append(t)
    return targets


def resolve(targets: list[str], wiki_files: list[str]):
    """按精校口径解析：返回 (resolved 页面集, 断链/歧义明细, path 出现计数)。"""
    by_stem: dict[str, list[str]] = {}
    for f in wiki_files:
        by_stem.setdefault(Path(f).stem, []).append(f)

    resolved: set[str] = set()
    broken: list[tuple[str, str]] = []
    seen: Counter[str] = Counter()
    for t in targets:
        if t.startswith("raw/") or t.lower().endswith(ATTACH_EXT):
            continue  # 排除项不计入
        hits = {f for f in wiki_files if f == t or f == "wiki/" + t or f.endswith("/" + t)}
        stem_hits = by_stem.get(t, [])
        if len(hits) == 1:
            page = next(iter(hits))
        elif len(hits) > 1:
            broken.append((t, "歧义: " + " | ".join(sorted(hits))))
            continue
        elif len(stem_hits) == 1:
            page = stem_hits[0]
        elif len(stem_hits) > 1:
            broken.append((t, "歧义: " + " | ".join(stem_hits)))
            continue
        else:
            broken.append((t, "未命中"))
            continue
        seen[page] += 1
        resolved.add(page)
    return resolved, broken, seen


def read_footer(vault: Path) -> dict[str, int] | None:
    """解析 index.md 页脚旧六变量（供漂移对照）。"""
    text = (vault / "index.md").read_text(encoding="utf-8")
    ms, mh = FOOT_STAT.search(text), FOOT_HEALTH.search(text)
    if not ms or not mh:
        return None
    return {
        "indexed_page_count": int(ms.group(1)),
        "wiki_file_count": int(ms.group(2)),
        "registered_domain_count": int(ms.group(3)),
        "missing_count": int(mh.group(1)),
        "broken_count": int(mh.group(2)),
        "duplicate_count": int(mh.group(3)),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="obsidian-llm-wiki 六变量精校")
    ap.add_argument("vault_root", help="vault 根目录（含 index.md 与 wiki/）")
    ap.add_argument("--json", action="store_true", help="输出 JSON（机读）")
    args = ap.parse_args()

    vault = Path(args.vault_root)
    if not vault.is_dir():
        print(f"错误：vault 根不存在：{vault}", file=sys.stderr)
        return 2
    if not (vault / "index.md").is_file():
        print(f"错误：{vault / 'index.md'} 不存在", file=sys.stderr)
        return 2

    wiki_files = scan_wiki(vault)
    domains, domain_notes = count_registered_domains(vault)
    targets = extract_targets(vault)
    resolved, broken, seen = resolve(targets, wiki_files)

    missing = [f for f in wiki_files if f not in resolved]
    duplicates = {p: c for p, c in seen.items() if c > 1}
    result = {
        "indexed_page_count": len(resolved),
        "wiki_file_count": len(wiki_files),
        "registered_domain_count": domains,
        "missing_count": len(missing),
        "broken_count": len(broken),
        "duplicate_count": sum(c - 1 for c in duplicates.values()),
    }

    footer = read_footer(vault)
    drift = None
    if footer:
        drift = {k: {"footer": footer[k], "scan": result[k]}
                 for k in result if footer[k] != result[k]}
    footer_match = footer is not None and not drift

    payload = {
        "vault": str(vault),
        **result,
        "missing": missing,
        "broken": [{"target": t, "reason": r} for t, r in broken],
        "duplicates": duplicates,
        "domain_notes": domain_notes,
        "footer": footer,
        "footer_match": footer_match,
        "drift": drift,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    six = (f"{result['indexed_page_count']}/{result['wiki_file_count']}/"
           f"{result['registered_domain_count']}")
    health = f"{result['missing_count']}/{result['broken_count']}/{result['duplicate_count']}"
    print(f"== obsidian-llm-wiki 精校（references/index_stat.py）==")
    print(f"vault: {vault}")
    print(f"wiki_file_count:         {result['wiki_file_count']}")
    print(f"indexed_page_count:      {result['indexed_page_count']}")
    print(f"registered_domain_count: {result['registered_domain_count']}")
    print(f"missing_count:           {result['missing_count']}")
    print(f"broken_count:            {result['broken_count']}")
    print(f"duplicate_count:         {result['duplicate_count']}")
    for m in missing:
        print(f"  MISSING: {m}")
    for t, r in broken:
        print(f"  BROKEN:  {t} ({r})")
    for p, c in duplicates.items():
        print(f"  DUP:     {p} ×{c}")
    for n in domain_notes:
        print(f"  NOTE:    {n}")
    if footer is None:
        print("页脚对照: 未找到统计行/索引健康行（页脚格式异常）")
    elif footer_match:
        print(f"页脚对照: 一致（六变量 {six} | {health}）")
    else:
        print(f"页脚对照: 漂移！扫描值 {six} | {health}，页脚旧值见 --json；按『统计漂移修正』用扫描值覆盖")
    print(f"六变量: {six} | {health}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
