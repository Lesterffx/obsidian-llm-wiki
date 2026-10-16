"""Sample a local raw video without changing it or contacting a media service."""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any


VIDEO_EXTENSIONS = {'.mp4', '.mov', '.webm', '.m4v', '.mkv', '.avi', '.ogv'}


def validate_task_id(task_id: str) -> None:
    if task_id in {'.', '..'} or not re.fullmatch(r'[A-Za-z0-9._-]+', task_id):
        raise ValueError('task-id must be a single safe path component')


def require_inside(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError('path is outside the permitted source or task scope')
    return resolved


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def sample_times(duration: float, frame_interval: float = .1) -> list[float]:
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('video duration must be finite and positive')
    end = duration - min(max(.1, frame_interval), duration / 2)
    count = math.floor(end / 5) + 1
    if count >= 60:
        return [end * index / 59 for index in range(60)]
    times = [float(index * 5) for index in range(count)]
    if end > times[-1] + .001:
        times.append(end)
    return times


def run_tool(arguments: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(arguments, check=True, capture_output=True, text=True,
                          encoding='utf-8', errors='replace', timeout=120)


def find_tools() -> tuple[str, str]:
    tools = tuple(shutil.which(name) for name in ('ffprobe', 'ffmpeg'))
    if not all(tools):
        raise FileNotFoundError('existing ffprobe and ffmpeg are required; nothing was installed')
    return tools


def probe(ffprobe: str, source: Path) -> dict[str, Any]:
    output = run_tool([ffprobe, '-v', 'error', '-protocol_whitelist', 'file',
                       '-show_entries', 'format=duration:stream=index,codec_type,width,height,start_time,duration,avg_frame_rate:stream_disposition=attached_pic',
                       '-of', 'json', '-i', str(source)])
    metadata = json.loads(output.stdout)
    streams = [s for s in metadata.get('streams', []) if s.get('codec_type') == 'video'
               and not s.get('disposition', {}).get('attached_pic')]
    if not streams:
        raise ValueError('no video stream found')
    stream = streams[0]
    duration = float(stream.get('duration') or metadata.get('format', {}).get('duration', 'nan'))
    sample_times(duration)
    start = float(stream.get('start_time', 0))
    if not math.isfinite(start):
        raise ValueError('invalid video start timestamp')
    try:
        rate = float(Fraction(stream.get('avg_frame_rate', '0/1')))
        frame_interval = 1 / rate if rate > 0 else .1
    except (ValueError, ZeroDivisionError):
        frame_interval = .1
    return {'duration_seconds': duration, 'start_time_seconds': start,
            'frame_interval': frame_interval,
            'stream_index': stream.get('index', 0),
            'width': stream.get('width'), 'height': stream.get('height')}


def validate_input(args: argparse.Namespace) -> tuple[Path, Path, Path, Path, Path]:
    validate_task_id(args.task_id)
    vault = Path(args.vault_root).resolve(strict=True)
    if not vault.is_dir():
        raise ValueError('vault-root must be a directory')
    raw = require_inside((vault / 'raw').resolve(strict=True), vault)
    scope = require_inside(Path(args.source_scope).resolve(strict=True), raw)
    source = require_inside(Path(args.input).resolve(strict=True), raw)
    require_inside(source, scope)
    if not source.is_file() or source.suffix.lower() not in VIDEO_EXTENSIONS:
        raise ValueError('input must be an existing supported local video')
    protected_tmp = require_inside(vault / 'tmp', vault)
    if protected_tmp.is_relative_to(raw):
        raise ValueError('temporary output cannot be under raw')
    workflow = require_inside(protected_tmp / 'obsidian-llm-wiki', protected_tmp)
    task = require_inside(workflow / args.task_id, workflow)
    if task.exists():
        raise FileExistsError('task directory already exists; refusing to overwrite')
    return source, raw, scope, task, protected_tmp


def subtitle_candidate(source: Path, raw: Path, scope: Path) -> dict[str, Any]:
    candidates = [source.with_suffix(ext) for ext in ('.srt', '.vtt')
                  if source.with_suffix(ext).is_file()]
    allowed = []
    for candidate in candidates:
        try:
            allowed.append(require_inside(require_inside(candidate, raw), scope))
        except ValueError:
            continue
    if candidates and not allowed:
        return {'status': 'out_of_scope'}
    if len(allowed) > 1:
        return {'status': 'ambiguous', 'candidates': [str(p) for p in allowed]}
    if not allowed:
        return {'status': 'absent'}
    return {'status': 'available', 'path': str(allowed[0]), 'sha256': digest(allowed[0])}


def extract_frame(ffmpeg: str, source: Path, output: Path, requested: float,
                  start_time: float, stream_index: int = 0) -> dict[str, Any]:
    record = {'requested_seconds': requested, 'path': str(output),
              'source_pts_seconds': None, 'timeline_seconds': None}
    try:
        result = run_tool([ffmpeg, '-hide_banner', '-nostdin', '-loglevel', 'info',
                           '-protocol_whitelist', 'file', '-ss', f'{requested:.6f}',
                           '-copyts', '-i', str(source), '-map', f'0:{stream_index}',
                           '-frames:v', '1', '-vf', 'scale=min(1600\\,iw):-2,showinfo',
                           '-an', '-sn', '-dn', '-fps_mode', 'passthrough', '-n', str(output)])
        if not output.is_file():
            raise ValueError('decoder produced no frame')
        match = re.search(r'\bn:\s*0\s+pts:\s*\S+\s+pts_time:([\d.eE+-]+)', result.stderr)
        pts = float(match.group(1)) if match else None
        if pts is not None and math.isfinite(pts):
            record.update(status='sampled', source_pts_seconds=pts,
                          timeline_seconds=pts - start_time)
        else:
            record['status'] = 'sampled_timestamp_unknown'
    except (subprocess.SubprocessError, OSError, ValueError) as exc:
        record.update(status='failed', error=type(exc).__name__)
    return record


def process(args: argparse.Namespace) -> dict[str, Any]:
    # This branch intentionally precedes all source, subtitle, tool and output IO.
    if args.no_video:
        return {'status': 'skipped', 'reason': '--no-video', 'writes': 0}
    source, raw, scope, task, protected_tmp = validate_input(args)
    ffprobe, ffmpeg = find_tools()
    info = probe(ffprobe, source)
    before = digest(source)
    subtitle = subtitle_candidate(source, raw, scope)
    cleanup_path = task / 'created_files.json'
    report_path = task / 'video-manifest.json'
    frames_dir = task / 'frames'
    created_files: list[str] = []
    created_dirs = [str(task)]
    report = dict(info, source=str(source), source_sha256=before,
                  size_bytes=source.stat().st_size, subtitle=subtitle,
                  sampling='5-second target interval; at most 60 samples including the final segment',
                  coverage='sampled visual evidence only; no audio transcription',
                  status='unreadable', frames=[])
    task.mkdir(parents=True, exist_ok=False)

    def cleanup_manifest() -> None:
        cleanup = {'task_root': str(task), 'created_files': created_files + [str(cleanup_path)],
                   'created_directories': list(reversed(created_dirs)),
                   'conditional_cleanup_directory': str(task.parent),
                   'protected_tmp_root': str(protected_tmp)}
        cleanup_path.write_text(json.dumps(cleanup, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    # Register outputs before decoding so controlled failures remain cleanable.
    try:
        cleanup_manifest()
        frames_dir.mkdir()
        created_dirs.append(str(frames_dir))
        cleanup_manifest()
        for index, requested in enumerate(sample_times(info['duration_seconds'], info['frame_interval']), 1):
            output = frames_dir / f'frame-{index:03d}.jpg'
            frame = extract_frame(ffmpeg, source, output, requested,
                                  info['start_time_seconds'], info['stream_index'])
            frame['index'] = index
            report['frames'].append(frame)
            if output.is_file():
                created_files.append(str(output))
            cleanup_manifest()
        good = sum(f['status'].startswith('sampled') for f in report['frames'])
        report['status'] = 'sampled' if good == len(report['frames']) else ('partial' if good else 'unreadable')
    finally:
        try:
            report['source_unchanged'] = digest(source) == before
        except OSError:
            report['source_unchanged'] = False
        if not report['source_unchanged']:
            report['status'] = 'source_changed'
        try:
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        finally:
            if report_path.is_file():
                created_files.append(str(report_path))
            cleanup_manifest()
    return {'status': report['status'], 'frame_count': len(report['frames']),
            'source_unchanged': report['source_unchanged'],
            'video_manifest': str(report_path), 'cleanup_manifest': str(cleanup_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--vault-root', required=True, type=Path)
    parser.add_argument('--source-scope', required=True, type=Path)
    parser.add_argument('--task-id', required=True)
    parser.add_argument('--no-video', action='store_true')
    args = parser.parse_args()
    try:
        result = process(args)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        reason = ('local ffprobe/ffmpeg failed or timed out; inspect the private source/tool state'
                  if isinstance(exc, subprocess.SubprocessError) else str(exc)[:300])
        print(json.dumps({'status': 'unreadable', 'error': type(exc).__name__,
                          'reason': reason}))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 2 if result['status'] in {'unreadable', 'source_changed'} else 0


if __name__ == '__main__':
    raise SystemExit(main())
