#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""obsidian-llm-wiki —— defer 队列合并脚本（/sync 的机械执行部分）。

职责边界（index.md 条目插入与三处页脚同步由执行 /sync 的 agent 完成，不在本脚本范围）：
  1. 取锁/释放锁：logs/queue/.sync.lock（O_CREAT|O_EXCL；过期锁单文件删除后重取）
  2. 按文件名时间序校验 logs/queue/*.md 队列片段（片段模板见 assets/queue-fragment.md）
  3. 把片段中的 log 条目按序追加到 log.md（二进制追加，UTF-8 字节精确，规避大文件 heredoc 截断风险）
  4. 追加前后完整性验证（前缀 SHA-256 零改动、字节增量对账、条目标题全库唯一、末尾换行）
  5. 成功后逐个单文件删除已合并/已重复跳过的片段（无递归、无通配符）
  6. 全程输出 JSON 报告（stdout）

只用标准库；路径一律 pathlib；文本显式 UTF-8。
退出码：0 成功（含空队列/无可合并项）；2 用法或路径错误；3 锁被占用；5 追加后验证失败
（此时片段保留，修复后可重跑——重跑按条目标题去重，幂等）。
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

QUEUE_MARKER = "obsidian-llm-wiki queue v1"
LOCK_NAME = ".sync.lock"
META_KEYS = ("task", "date", "page", "section", "summary")
META_RE = re.compile(r"^<!--\s*([a-zA-Z_-]+):\s*(.*?)\s*-->\s*$")
HEADLINE_RE = re.compile(r"^##\s*\[")
FENCES = {
    "index": ("<!-- index-entry -->", "<!-- /index-entry -->"),
    "log": ("<!-- log-entry -->", "<!-- /log-entry -->"),
}


def emit(payload, code):
    payload["exit_code"] = code
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    sys.exit(code)


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def parse_fragment(path):
    frag = {
        "file": path.name,
        "valid": True,
        "errors": [],
        "task": None,
        "date": None,
        "page": None,
        "section": None,
        "summary": None,
        "index_entry": None,
        "log_body": None,
        "log_title": None,
        "append_bytes": 0,
    }
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        frag["valid"] = False
        frag["errors"].append("read_failed: %s" % exc)
        return frag

    if QUEUE_MARKER not in text:
        frag["errors"].append("missing queue marker: %s" % QUEUE_MARKER)

    for line in text.splitlines():
        m = META_RE.match(line.strip())
        if m and m.group(1) in META_KEYS and frag[m.group(1)] is None:
            frag[m.group(1)] = m.group(2)

    for key, (begin, end) in FENCES.items():
        if begin not in text or end not in text:
            frag["errors"].append("missing fence: %s ... %s" % (begin, end))
            continue
        body = text.split(begin, 1)[1].split(end, 1)[0]
        if key == "index":
            frag["index_entry"] = body.strip()
        else:
            frag["log_body"] = body

    if frag["index_entry"] is not None and not frag["index_entry"]:
        frag["errors"].append("empty index-entry fence")

    if frag["log_body"] is not None:
        core = frag["log_body"].strip("\n")
        if not core:
            frag["errors"].append("empty log-entry fence")
        else:
            frag["log_body"] = "\n" + core + "\n"
            for line in core.splitlines():
                if HEADLINE_RE.match(line.strip()):
                    frag["log_title"] = line.strip()
                    break
            if frag["log_title"] is None:
                frag["errors"].append("log-entry has no '## [' heading")

    if not frag["page"]:
        frag["errors"].append("missing page meta")
    if not frag["section"]:
        frag["errors"].append("missing section meta")

    if frag["date"] and frag["log_title"]:
        m = re.match(r"^##\s*\[(\d{4}-\d{2}-\d{2})\]", frag["log_title"])
        if m and m.group(1) != frag["date"]:
            frag["errors"].append(
                "date meta %s != log title date %s" % (frag["date"], m.group(1))
            )

    if frag["errors"]:
        frag["valid"] = False
    return frag


def normalized_page(vault, raw_page):
    page = raw_page.strip().replace("\\", "/")
    if page.startswith("./"):
        page = page[2:]
    if not page.startswith("wiki/"):
        return None
    resolved = (vault / page).resolve()
    try:
        resolved.relative_to(vault.resolve())
    except ValueError:
        return None
    return page


def acquire_lock(queue_dir, lock_minutes):
    lock_path = queue_dir / LOCK_NAME
    queue_dir.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(
                fd,
                ("pid=%d time=%s\n" % (os.getpid(), time.strftime("%Y-%m-%dT%H:%M:%S"))).encode("utf-8"),
            )
            os.close(fd)
            return lock_path
        except FileExistsError:
            age = time.time() - lock_path.stat().st_mtime
            if age < lock_minutes * 60:
                emit(
                    {
                        "status": "lock_held",
                        "lock_path": str(lock_path),
                        "lock_age_seconds": int(age),
                        "lock_minutes": lock_minutes,
                        "message": "another /sync run appears active; retry later",
                    },
                    3,
                )
            lock_path.unlink()  # 过期锁：单文件删除后重取
    emit({"status": "lock_unacquirable", "lock_path": str(lock_path)}, 3)


def main():
    ap = argparse.ArgumentParser(description="obsidian-llm-wiki defer queue flush")
    ap.add_argument("--vault-root", required=True, help="vault 根目录")
    ap.add_argument("--dry-run", action="store_true", help="只校验与报告，零写入")
    ap.add_argument("--lock-minutes", type=int, default=15, help="锁新鲜度阈值（分钟）")
    args = ap.parse_args()
    if args.lock_minutes <= 0:
        emit({"error": "--lock-minutes must be positive"}, 2)

    vault = Path(args.vault_root)
    if not vault.is_dir():
        emit({"error": "vault_root is not a directory: %s" % str(vault)}, 2)

    queue_dir = vault / "logs" / "queue"
    log_path = vault / "log.md"
    if not log_path.is_file():
        emit({"error": "log.md not found (vault not initialized?)", "log_path": str(log_path)}, 2)

    if not queue_dir.is_dir():
        emit(
            {
                "status": "empty_queue",
                "queue_dir": str(queue_dir),
                "dry_run": args.dry_run,
                "message": "queue dir missing; nothing to merge (footer/stats refresh is agent work)",
            },
            0,
        )

    frag_files = sorted(p for p in queue_dir.glob("*.md") if p.is_file())
    if not frag_files:
        emit(
            {
                "status": "empty_queue",
                "queue_dir": str(queue_dir),
                "dry_run": args.dry_run,
                "fragments_total": 0,
                "message": "no fragments in queue",
            },
            0,
        )

    frags = [parse_fragment(p) for p in frag_files]

    log_bytes = log_path.read_bytes()
    log_text = log_bytes.decode("utf-8", errors="replace")

    merged, skipped_dup, dropped_page, invalid = [], [], [], []
    seen_titles = set()
    for f in frags:
        if not f["valid"]:
            invalid.append({"file": f["file"], "errors": f["errors"]})
            continue
        page = normalized_page(vault, f["page"])
        if page is None or not (vault / page).is_file():
            dropped_page.append({"file": f["file"], "page": f["page"]})
            continue
        f["page"] = page
        title = f["log_title"]
        if title in seen_titles or title in log_text:
            skipped_dup.append({"file": f["file"], "title": title})
            continue
        seen_titles.add(title)
        f["append_bytes"] = len(f["log_body"].encode("utf-8"))
        merged.append(f)

    report = {
        "status": "dry_run" if args.dry_run else "merged",
        "vault_root": str(vault),
        "queue_dir": str(queue_dir),
        "dry_run": args.dry_run,
        "fragments_total": len(frags),
        "merged": [
            {
                "file": f["file"],
                "task": f["task"],
                "page": f["page"],
                "section": f["section"],
                "title": f["log_title"],
                "append_bytes": f["append_bytes"],
            }
            for f in merged
        ],
        "skipped_duplicate": skipped_dup,
        "dropped_missing_page": dropped_page,
        "invalid": invalid,
        "log": {
            "path": str(log_path),
            "before_bytes": len(log_bytes),
        },
    }
    planned_bytes = sum(f["append_bytes"] for f in merged)
    report["log"]["planned_append_bytes"] = planned_bytes

    if args.dry_run:
        report["message"] = "dry run: no writes performed"
        emit(report, 0)

    if not merged and not skipped_dup:
        report["message"] = (
            "nothing to append (all fragments invalid or dropped); "
            "handle invalid/dropped fragments then re-run"
        )
        emit(report, 0)

    lock_path = acquire_lock(queue_dir, args.lock_minutes)
    try:
        prefix = b"" if log_bytes.endswith(b"\n") else b"\n"
        appended = prefix
        with log_path.open("ab") as fh:
            if prefix:
                fh.write(prefix)
            for f in merged:
                chunk = f["log_body"].encode("utf-8")
                fh.write(chunk)
                appended += chunk

        new_bytes = log_path.read_bytes()
        ok_len = len(new_bytes) == len(log_bytes) + len(appended)
        ok_prefix = sha256_hex(new_bytes[: len(log_bytes)]) == sha256_hex(log_bytes)
        ok_tail = new_bytes.endswith(b"\n")
        new_text = new_bytes.decode("utf-8", errors="replace")
        bad_titles = [f["log_title"] for f in merged if new_text.count(f["log_title"]) != 1]

        report["log"]["after_bytes"] = len(new_bytes)
        report["log"]["appended_bytes"] = len(appended)
        report["log"]["prefix_sha256_unchanged"] = ok_prefix
        report["log"]["ends_with_newline"] = ok_tail
        report["log"]["titles_not_unique"] = bad_titles

        if not (ok_len and ok_prefix and ok_tail and not bad_titles):
            report["status"] = "verification_failed"
            report["message"] = (
                "append verification failed; fragments retained; fix and re-run "
                "(title-dedup makes re-run idempotent)"
            )
            emit(report, 5)

        deleted, delete_failed = [], []
        for f in merged + [fr for fr in frags if fr["file"] in {s["file"] for s in skipped_dup}]:
            try:
                (queue_dir / f["file"]).unlink()
                deleted.append(f["file"])
            except OSError as exc:
                delete_failed.append({"file": f["file"], "error": str(exc)})
        report["fragments_deleted"] = deleted
        report["fragments_delete_failed"] = delete_failed
        report["message"] = (
            "merged %d fragment(s); %d skipped as duplicate; "
            "invalid/dropped fragments retained for agent handling"
            % (len(merged), len(skipped_dup))
        )
        emit(report, 0)
    finally:
        try:
            lock_path.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    main()
