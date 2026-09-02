from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import fitz
from pypdf import PdfReader


SAFE_TASK_ID = re.compile(r"^[A-Za-z0-9._-]+$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preprocess a PDF for obsidian-llm-wiki without modifying raw sources."
    )
    parser.add_argument("--input", required=True, type=Path, help="Absolute PDF path")
    parser.add_argument(
        "--vault-root", required=True, type=Path, help="Absolute Obsidian vault root"
    )
    parser.add_argument(
        "--task-id",
        required=True,
        help="Unique task id using only letters, digits, dot, underscore, and hyphen",
    )
    return parser.parse_args()


def validate_task_id(task_id: str) -> None:
    if task_id in {".", ".."} or not SAFE_TASK_ID.fullmatch(task_id):
        raise ValueError(
            "task-id must use only letters, digits, dot, underscore, and hyphen"
        )


def quality_metrics(text: str) -> dict[str, Any]:
    length = len(text)
    replacement_count = text.count("\ufffd")
    control_count = sum(
        1 for char in text if ord(char) < 32 and char not in "\n\r\t"
    )
    replacement_ratio = replacement_count / max(length, 1)
    control_ratio = control_count / max(length, 1)
    repeated_replacement = bool(re.search(r"\ufffd{2,}|���", text))
    acceptable = bool(text.strip()) and replacement_ratio <= 0.01 and control_ratio <= 0.005 and not repeated_replacement
    penalty = replacement_count * 100 + control_count * 50 + (1000 if repeated_replacement else 0)
    return {
        "chars": length,
        "replacement_count": replacement_count,
        "replacement_ratio": round(replacement_ratio, 6),
        "control_count": control_count,
        "control_ratio": round(control_ratio, 6),
        "repeated_replacement": repeated_replacement,
        "acceptable": acceptable,
        "penalty": penalty,
    }


def choose_text(pypdf_text: str, pymupdf_text: str) -> tuple[str, str, str, dict[str, Any], dict[str, Any]]:
    pypdf_metrics = quality_metrics(pypdf_text)
    pymupdf_metrics = quality_metrics(pymupdf_text)
    if pypdf_metrics["acceptable"]:
        return pypdf_text, "pypdf", "ok", pypdf_metrics, pymupdf_metrics
    if pymupdf_metrics["acceptable"] and pymupdf_metrics["penalty"] < pypdf_metrics["penalty"]:
        return pymupdf_text, "pymupdf", "fallback", pypdf_metrics, pymupdf_metrics
    if not pypdf_text.strip() and not pymupdf_text.strip():
        return "", "none", "empty_text", pypdf_metrics, pymupdf_metrics
    return "", "none", "corrupt_text", pypdf_metrics, pymupdf_metrics


def jsonable_metadata(metadata: Any) -> dict[str, Any]:
    if metadata is None:
        return {}
    try:
        return {str(key): value for key, value in dict(metadata).items()}
    except Exception:
        return {"value": str(metadata)}


def main() -> int:
    args = parse_args()
    validate_task_id(args.task_id)

    input_pdf = args.input.resolve(strict=True)
    vault_root = args.vault_root.resolve(strict=True)
    if not input_pdf.is_file() or input_pdf.suffix.lower() != ".pdf":
        raise ValueError("input must be an existing PDF file")
    if not vault_root.is_dir():
        raise ValueError("vault-root must be an existing directory")

    protected_tmp_root = (vault_root / "tmp").resolve()
    task_root = (protected_tmp_root / "obsidian-llm-wiki" / args.task_id).resolve()
    allowed_parent = (protected_tmp_root / "obsidian-llm-wiki").resolve()
    if task_root.parent != allowed_parent:
        raise ValueError("task root escaped tmp/obsidian-llm-wiki")
    if task_root.exists():
        raise FileExistsError(f"task root already exists: {task_root}")

    workflow_root_created_by_task = not allowed_parent.exists()
    task_root.mkdir(parents=True, exist_ok=False)
    created_files: list[Path] = []
    created_directories: list[Path] = [task_root.resolve()]
    image_dir = task_root / "images"
    rendered_dir = task_root / "rendered_pages"
    manifest_path = task_root / "created_files.json"

    def ensure_directory(path: Path) -> None:
        if not path.exists():
            path.mkdir(parents=False, exist_ok=False)
            created_directories.append(path.resolve())

    def write_text(path: Path, content: str) -> None:
        ensure_directory(path.parent)
        with path.open("w", encoding="utf-8") as handle:
            created_files.append(path.resolve())
            handle.write(content)

    def write_bytes(path: Path, content: bytes) -> None:
        ensure_directory(path.parent)
        with path.open("wb") as handle:
            created_files.append(path.resolve())
            handle.write(content)

    try:
        source_bytes = input_pdf.read_bytes()
        source_hash = hashlib.sha256(source_bytes).hexdigest()
        pypdf_reader = PdfReader(input_pdf)
        pymupdf_document = fitz.open(input_pdf)
        if len(pypdf_reader.pages) != pymupdf_document.page_count:
            raise ValueError("page count differs between pypdf and PyMuPDF")

        pages: list[dict[str, Any]] = []
        page_text_parts: list[str] = []
        image_rows: list[dict[str, Any]] = []
        unique_images: dict[int, dict[str, Any]] = {}
        visual_pages: list[int] = []

        for page_number in range(1, pymupdf_document.page_count + 1):
            fitz_page = pymupdf_document[page_number - 1]
            try:
                pypdf_text = (pypdf_reader.pages[page_number - 1].extract_text() or "").strip()
            except Exception as exc:
                pypdf_text = ""
                pypdf_error = f"{type(exc).__name__}: {exc}"
            else:
                pypdf_error = None
            try:
                pymupdf_text = fitz_page.get_text("text", sort=True).strip()
            except Exception as exc:
                pymupdf_text = ""
                pymupdf_error = f"{type(exc).__name__}: {exc}"
            else:
                pymupdf_error = None

            selected_text, extractor, status, pypdf_quality, pymupdf_quality = choose_text(
                pypdf_text, pymupdf_text
            )
            requires_visual = status in {"empty_text", "corrupt_text"}
            rendered_path: Path | None = None
            if requires_visual:
                visual_pages.append(page_number)
                pixmap = fitz_page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                rendered_path = rendered_dir / f"page-{page_number:03d}.png"
                write_bytes(rendered_path, pixmap.tobytes("png"))

            images = fitz_page.get_images(full=True)
            for occurrence, image_info in enumerate(images, start=1):
                xref = int(image_info[0])
                if xref not in unique_images:
                    image = pymupdf_document.extract_image(xref)
                    extension = str(image.get("ext", "bin"))
                    image_path = image_dir / f"xref-{xref}.{extension}"
                    write_bytes(image_path, image["image"])
                    unique_images[xref] = {
                        "xref": xref,
                        "filename": image_path.name,
                        "absolute_path": str(image_path.resolve()),
                        "width": int(image_info[2]),
                        "height": int(image_info[3]),
                        "sha256": hashlib.sha256(image["image"]).hexdigest(),
                        "pages": [],
                    }
                unique_images[xref]["pages"].append(page_number)
                image_rows.append(
                    {
                        "manifest_index": len(image_rows) + 1,
                        "page": page_number,
                        "occurrence": occurrence,
                        "xref": xref,
                        "filename": unique_images[xref]["filename"],
                        "absolute_path": unique_images[xref]["absolute_path"],
                        "width": int(image_info[2]),
                        "height": int(image_info[3]),
                        "status": "extracted",
                    }
                )

            page_record = {
                "page": page_number,
                "status": status,
                "selected_extractor": extractor,
                "requires_visual": requires_visual,
                "rendered_page": str(rendered_path.resolve()) if rendered_path else None,
                "text_chars": len(selected_text),
                "text": selected_text,
                "image_occurrences": len(images),
                "pypdf_quality": pypdf_quality,
                "pymupdf_quality": pymupdf_quality,
                "pypdf_error": pypdf_error,
                "pymupdf_error": pymupdf_error,
            }
            pages.append(page_record)
            page_body = selected_text if selected_text else f"[第 {page_number} 页需视觉读取：{status}]"
            page_text_parts.append(f"## 第 {page_number} 页\n\n{page_body}\n")

        metadata = {
            "source": str(input_pdf),
            "sha256": source_hash,
            "file_size": len(source_bytes),
            "page_count": pymupdf_document.page_count,
            "pypdf_metadata": jsonable_metadata(pypdf_reader.metadata),
            "pymupdf_metadata": pymupdf_document.metadata,
            "text_priority": ["pypdf", "pymupdf", "visual"],
            "visual_pages": visual_pages,
        }
        write_text(
            task_root / "metadata.json",
            json.dumps(metadata, ensure_ascii=False, indent=2),
        )
        write_text(
            task_root / "pages.json",
            json.dumps(pages, ensure_ascii=False, indent=2),
        )
        write_text(task_root / "page_text.md", "\n".join(page_text_parts))

        image_fields = [
            "manifest_index",
            "page",
            "occurrence",
            "xref",
            "filename",
            "absolute_path",
            "width",
            "height",
            "status",
        ]
        image_manifest_path = task_root / "image_manifest.csv"
        with image_manifest_path.open("w", encoding="utf-8-sig", newline="") as handle:
            created_files.append(image_manifest_path.resolve())
            writer = csv.DictWriter(handle, fieldnames=image_fields)
            writer.writeheader()
            writer.writerows(image_rows)

        unique_fields = [
            "unique_index",
            "xref",
            "filename",
            "absolute_path",
            "pages",
            "occurrence_count",
            "width",
            "height",
            "sha256",
            "status",
        ]
        unique_rows: list[dict[str, Any]] = []
        for unique_index, item in enumerate(unique_images.values(), start=1):
            pages_for_image = list(item["pages"])
            unique_rows.append(
                {
                    "unique_index": unique_index,
                    "xref": item["xref"],
                    "filename": item["filename"],
                    "absolute_path": item["absolute_path"],
                    "pages": ",".join(str(page) for page in pages_for_image),
                    "occurrence_count": len(pages_for_image),
                    "width": item["width"],
                    "height": item["height"],
                    "sha256": item["sha256"],
                    "status": "extracted",
                }
            )
        unique_manifest_path = task_root / "unique_image_manifest.csv"
        with unique_manifest_path.open("w", encoding="utf-8-sig", newline="") as handle:
            created_files.append(unique_manifest_path.resolve())
            writer = csv.DictWriter(handle, fieldnames=unique_fields)
            writer.writeheader()
            writer.writerows(unique_rows)

        summary = {
            "task_root": str(task_root),
            "source_sha256": source_hash,
            "pages": pymupdf_document.page_count,
            "text_chars": sum(page["text_chars"] for page in pages),
            "visual_pages": visual_pages,
            "image_occurrences": len(image_rows),
            "unique_images": len(unique_rows),
        }
    except Exception:
        summary = {
            "task_root": str(task_root),
            "status": "failed",
            "error": f"{type(sys.exc_info()[1]).__name__}: {sys.exc_info()[1]}",
        }
        raise
    finally:
        cleanup_order = [str(path) for path in created_files] + [str(manifest_path.resolve())]
        unique_created_directories = list(dict.fromkeys(created_directories))
        directory_cleanup_order = [
            str(path)
            for path in sorted(
                unique_created_directories,
                key=lambda item: len(item.parts),
                reverse=True,
            )
        ]
        manifest = {
            "task_root": str(task_root),
            "created_files": cleanup_order,
            "cleanup_order": cleanup_order,
            "created_directories": directory_cleanup_order,
            "conditional_cleanup_directory": str(allowed_parent),
            "workflow_root_created_by_task": workflow_root_created_by_task,
            "protected_tmp_root": str(protected_tmp_root),
        }
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    summary["created_files"] = cleanup_order
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
