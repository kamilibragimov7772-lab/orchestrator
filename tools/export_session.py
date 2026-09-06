# Orchestrator stack for Claude Code. Author: @kamil_ibrgmv - https://instagram.com/kamil_ibrgmv
"""Opt-in session export. Redacted by default when enabled; never mirrors/deletes projects.

Redaction recognizes credential patterns, not all personal or commercial data.
Configure a private VAULT_ROOT and an explicit transcript source root.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from secret_scan import COMPILED


def redact(value):
    if isinstance(value, dict): return {k: redact(v) for k, v in value.items()}
    if isinstance(value, list): return [redact(v) for v in value]
    if isinstance(value, str):
        for name, pattern in COMPILED.items(): value = pattern.sub('[REDACTED:' + name + ']', value)
    return value


def export(event, mode, vault, source_root):
    if mode == 'off': return {'status': 'skipped', 'reason': 'export disabled'}
    if mode not in {'redacted', 'full'}: raise ValueError('invalid export mode')
    if not vault or not source_root: raise ValueError('VAULT_ROOT and ORCHESTRATOR_TRANSCRIPT_ROOT required')
    source = Path(event.get('transcript_path', '')).resolve()
    root = Path(source_root).resolve()
    if not source.is_relative_to(root) or not source.is_file() or source.suffix != '.jsonl':
        raise ValueError('transcript must be a JSONL file within the configured source root')
    if source.stat().st_size > 25 * 1024 * 1024: raise ValueError('transcript exceeds 25 MiB budget')
    lines = source.read_text(encoding='utf-8-sig').splitlines()
    if not lines or not any(line.strip() for line in lines):
        raise ValueError('transcript is empty')
    records = []
    for line in lines:
        if not line.strip(): continue
        item = json.loads(line)
        if not isinstance(item, dict) or not item:
            raise ValueError('transcript contains non-record')
        records.append(item)
    if not records: raise ValueError('transcript has no records')
    if mode == 'redacted': records = [redact(record) for record in records]
    content = '\n'.join(json.dumps(x, ensure_ascii=False) for x in records) + '\n'
    dest = Path(vault).resolve() / '_session_exports'
    if dest.exists() and (dest.is_symlink() or dest.resolve().parent != Path(vault).resolve()):
        raise ValueError('export destination escapes vault')
    dest.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha256(str(source).encode()).hexdigest()[:24] + '.jsonl'
    target = dest / name
    fd, tmp = tempfile.mkstemp(prefix='.export-', dir=dest)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(content); stream.flush(); os.fsync(stream.fileno())
        os.replace(tmp, target)
    finally:
        Path(tmp).unlink(missing_ok=True)
    return {'status': 'success', 'mode': mode, 'records': len(records), 'destination': str(target)}


def main():
    try:
        mode = os.environ.get('ORCHESTRATOR_EXPORT_MODE', 'off')
        # A disabled exporter must not read the transcript or create directories.
        event = {} if mode == 'off' else json.loads(sys.stdin.buffer.read().decode('utf-8-sig'))
        result = export(event, mode, os.environ.get('VAULT_ROOT'), os.environ.get('ORCHESTRATOR_TRANSCRIPT_ROOT'))
    except (OSError, ValueError, TypeError):
        result = {'status': 'failed', 'reason': 'invalid configuration, transcript or filesystem operation'}
    print(json.dumps({'systemMessage': 'export-session: ' + json.dumps(result)}, ensure_ascii=True))
    return 1 if result['status'] == 'failed' else 0


if __name__ == '__main__':
    sys.exit(main())
