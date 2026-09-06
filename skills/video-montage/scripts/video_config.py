# Orchestrator stack for Claude Code. Author: @kamil_ibrgmv - https://instagram.com/kamil_ibrgmv
"""Explicit inputs for legacy video recipes. Never auto-select a personal folder."""
import math
import os
from pathlib import Path
import tempfile


def required_dir(name, create=False):
    value = os.environ.get(name)
    if not value: raise SystemExit(name + ' must explicitly name a task directory')
    path = Path(value).resolve()
    if create: path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir(): raise SystemExit(name + ' directory is missing')
    return str(path)


def output_file():
    value = os.environ.get('VIDEO_OUTPUT')
    if not value: raise SystemExit('VIDEO_OUTPUT must explicitly name the output MP4')
    path = Path(value).resolve()
    if path.suffix.lower() != '.mp4': raise SystemExit('VIDEO_OUTPUT must be an MP4 path')
    if path.exists(): raise SystemExit('VIDEO_OUTPUT already exists; choose a new output path')
    return str(path)


def clip_files(source, clip):
    if not clip or any(c in clip for c in '/\\:*?[]') or clip in {'.', '..'}:
        raise SystemExit('EDL clip must be a plain filename stem')
    root = Path(source).resolve()
    files = [p for p in root.iterdir() if p.stem == clip and p.suffix.lower() in {'.mov', '.mp4'}]
    if len(files) != 1 or not files[0].resolve().is_relative_to(root):
        raise SystemExit('EDL clip is missing, ambiguous or outside VIDEO_SOURCE: ' + clip)
    return [str(files[0])]


def validate_edl(edl, source=None):
    if not isinstance(edl, list) or not edl: raise SystemExit('EDL must be a nonempty list')
    for item in edl:
        if not isinstance(item, dict): raise SystemExit('EDL entry must be an object')
        try: seconds = float(item.get('dur_seconds', 0))
        except (TypeError, ValueError): raise SystemExit('EDL duration must be numeric')
        if not math.isfinite(seconds) or seconds <= 0: raise SystemExit('EDL duration must be positive and finite')
        clip = item.get('clip')
        if not isinstance(clip, str) or not clip.strip(): raise SystemExit('EDL clip missing')
        if source: clip_files(source, clip.strip())
    return edl


def scratch(work, prefix):
    return tempfile.mkdtemp(prefix=prefix + '-', dir=work)


def one_file(folder, suffix):
    root = Path(folder).resolve()
    found = [p for p in root.iterdir() if p.is_file() and p.suffix.lower() == suffix]
    if len(found) != 1 or not found[0].resolve().is_relative_to(root):
        raise SystemExit('Expected exactly one ' + suffix + ' file in the configured directory')
    return str(found[0])
