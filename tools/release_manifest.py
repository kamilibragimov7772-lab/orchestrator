"""SHA-256 manifest of the files a release actually ships.

Provenance in the plainest useful form: if a file changed after the manifest was
written, `--check` says so and names it. That is the whole claim -- no SLSA level
is asserted, and a manifest cannot prove anything about how the bytes were made.

Only tracked files are listed, so a stray artifact in the working tree cannot
quietly enter the manifest and look official. Directories that are evidence
rather than product (audit_9_5/evidence*) are excluded: they are large, they are
regenerated per round, and mixing them in would make every rerun look like a
change to the shipped code.

Usage:
    python tools/release_manifest.py --write      # refresh RELEASE_MANIFEST.txt
    python tools/release_manifest.py --check      # verify, exit 1 on drift
"""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'RELEASE_MANIFEST.txt'
EXCLUDE_PREFIXES = ('audit_9_5/evidence', 'RELEASE_MANIFEST.txt')


def tracked_files():
    out = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '-z'],
                         capture_output=True, timeout=120)
    names = out.stdout.decode('utf-8', 'replace').split('\0')
    return sorted(n for n in names
                  if n and not n.startswith(EXCLUDE_PREFIXES))


def digest(rel):
    data = (ROOT / rel).read_bytes()
    # Normalise line endings so a Windows checkout and a Linux one agree; the
    # manifest describes content, and git already rewrites EOL on checkout.
    if b'\0' not in data:
        data = data.replace(b'\r\n', b'\n')
    return hashlib.sha256(data).hexdigest()


def build():
    lines = []
    for rel in tracked_files():
        path = ROOT / rel
        if not path.is_file():
            continue
        lines.append('%s  %s' % (digest(rel), rel))
    return lines


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--write', action='store_true')
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    lines = build()
    if args.write:
        header = ['# SHA-256 of tracked release files, line endings normalised to LF.',
                  '# Regenerate: python tools/release_manifest.py --write',
                  '# Verify:     python tools/release_manifest.py --check',
                  '# Evidence directories are excluded by design (see module docstring).']
        MANIFEST.write_text('\n'.join(header + lines) + '\n', encoding='utf-8')
        print('%d files, manifest written' % len(lines))
        return 0

    if args.check:
        if not MANIFEST.is_file():
            print('no manifest: run --write first')
            return 1
        recorded = {}
        for line in MANIFEST.read_text(encoding='utf-8').splitlines():
            if line.startswith('#') or not line.strip():
                continue
            sha, _, rel = line.partition('  ')
            recorded[rel] = sha
        current = {rel: sha for sha, _, rel in
                   (l.partition('  ') for l in lines)}
        changed = sorted(r for r in recorded if current.get(r) != recorded[r])
        added = sorted(set(current) - set(recorded))
        removed = sorted(set(recorded) - set(current))
        for rel in changed:
            print('CHANGED %s' % rel)
        for rel in added:
            print('ADDED   %s' % rel)
        for rel in removed:
            print('REMOVED %s' % rel)
        if changed or added or removed:
            print('manifest does not match the working tree')
            return 1
        print('%d files match the manifest' % len(recorded))
        return 0

    p.error('pass --write or --check')


if __name__ == '__main__':
    sys.exit(main())
