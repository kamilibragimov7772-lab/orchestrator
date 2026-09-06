"""Portable PreToolUse guards. Heuristics complement native host permissions.

Malformed input fails closed and diagnostics never include the original payload.
Command detection is deliberately conservative; it is not a shell security boundary.
"""
import argparse
import json
import re
import shlex
import sys
from secret_scan import detect


def risky(command):
    # Never strip an echo containing substitutions: those execute before echo.
    command = re.sub(r"(?m)^\s*#.*$", '', command)
    command = re.sub(r'''\b(?:echo|printf|Write-Output)\s+(?:"[^"$`]*"|'[^']*')(?=\s*(?:$|[;|&\n]))''', ' ', command, flags=re.I)
    try:
        normalized = ' '.join(shlex.split(command, posix=True))
    except ValueError:
        return 'unparseable shell syntax; review with native permissions'
    candidates = [command, normalized]
    rules = {
        'force push': r'\bgit\s+(?:-[cC]\s+\S+\s+)*push\b[^;\n]*(?:--force(?:-with-lease)?\b|\s-[a-zA-Z]*f[a-zA-Z]*\b|\+[^\s]+:)',
        'hard reset': r'\bgit\s+reset\b[^;\n]*--hard\b',
        'branch deletion': r'\bgit\s+(?:push\b[^;\n]*--delete|branch\b[^;\n]*-D\b)',
        'recursive deletion': r'\brm\s+(?:-[a-zA-Z]*[rR][a-zA-Z]*\b|--recursive\b)|\bRemove-Item\b[^;\n]*-Recurse\b',
        'database deletion': r'\b(?:DROP\s+(?:TABLE|DATABASE)|TRUNCATE\s+TABLE)\b',
        'remote service change': r'\bssh\b[^;\n]*(?:systemctl\s+(?:restart|stop)|docker\s+(?:down|rm)|\brm\s)',
        'cron removal': r'\bcrontab\s+-r\b',
        'message send': r'api\.telegram\.org[^\s]*(?:sendMessage|sendPhoto|sendVideo|sendDocument)',
        'HTTP write': r'\bcurl\b[^;\n]*(?:-X\s*(?:POST|PUT|PATCH|DELETE)|--request[=\s]+(?:POST|PUT|PATCH|DELETE)|(?:--data(?:-raw|-binary|-urlencode)?|-d|--form|-F)(?:\s|=))',
        'encoded command': r'\b(?:powershell|pwsh)(?:\.exe)?\b[^;\n]*-(?:enc|encodedcommand)\b',
    }
    for label, pattern in rules.items():
        if any(re.search(pattern, text, re.I) for text in candidates): return label
    return None


def evaluate(kind, event):
    if not isinstance(event, dict) or not isinstance(event.get('tool_input'), dict):
        raise ValueError('missing tool_input')
    name = event.get('tool_name')
    data = event['tool_input']
    if kind == 'secret':
        field = {'Write': 'content', 'Edit': 'new_string', 'Bash': 'command', 'PowerShell': 'command'}.get(name)
        if not field: return None
        if not isinstance(data.get(field), str): raise ValueError('missing input field')
        types = detect(data[field])
        return 'credential pattern: ' + ', '.join(types) if types else None
    if name not in {'Bash', 'PowerShell'}: return None
    if not isinstance(data.get('command'), str): raise ValueError('missing command')
    return risky(data['command'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=['secret', 'risk'])
    kind = parser.parse_args().kind
    try:
        raw = sys.stdin.buffer.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024: raise ValueError('payload too large')
        event = json.loads(raw.decode('utf-8-sig'))
        reason = evaluate(kind, event)
    except (ValueError, UnicodeError, OSError):
        print(kind + '-guard: invalid input; operation NOT CHECKED and blocked', file=sys.stderr)
        return 2
    if reason:
        print(kind + '-guard: blocked (' + reason + '). Use the host permission workflow for authorized exceptions.', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
