# Orchestrator stack for Claude Code. Author: @kamil_ibrgmv - https://instagram.com/kamil_ibrgmv
"""Fetch a pinned Gitleaks release, verify SHA256, extract only the executable."""
import argparse
import hashlib
import io
import os
from pathlib import Path
import platform
import tarfile
from urllib.request import urlopen
import zipfile

VERSION = '8.30.1'
SHA256 = {
    'linux_x64.tar.gz': '551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb',
    'windows_x64.zip': 'd29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e',
}


def fetch(output):
    if platform.machine().lower() not in {'x86_64', 'amd64'}:
        raise ValueError('Pinned download supports x64 only; install Gitleaks for this platform separately')
    key = 'windows_x64.zip' if os.name == 'nt' else 'linux_x64.tar.gz' if platform.system() == 'Linux' else None
    if not key: raise ValueError('Unsupported download platform')
    url = f'https://github.com/gitleaks/gitleaks/releases/download/v{VERSION}/gitleaks_{VERSION}_{key}'
    data = urlopen(url, timeout=60).read()
    if hashlib.sha256(data).hexdigest() != SHA256[key]: raise ValueError('Gitleaks checksum mismatch')
    name = 'gitleaks.exe' if os.name == 'nt' else 'gitleaks'
    if key.endswith('.zip'):
        with zipfile.ZipFile(io.BytesIO(data)) as archive: exe = archive.read(name)
    else:
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
            member = archive.getmember(name)
            if not member.isfile(): raise ValueError('Expected a regular executable')
            exe = archive.extractfile(member).read()
    output.mkdir(parents=True, exist_ok=True)
    target = output / name
    target.write_bytes(exe); target.chmod(0o755)
    return target


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=Path('.tools'))
    args = p.parse_args()
    print(fetch(args.output).resolve())
