# PreToolUse hook: secret-guard (ECC AgentShield pattern, ported 2026-06-01)
# Blocks Write/Edit/Bash when a high-confidence credential token is about to be
# written into the knowledge base (vault / MEMORY / decisions-log) or a message.
# FAIL-SAFE: any error -> exit 0 (never breaks a legitimate operation).
# ASCII-only: PowerShell 5.1 mangles Cyrillic in .ps1 files without BOM.

$ErrorActionPreference = 'SilentlyContinue'
try {
    $raw = [Console]::In.ReadToEnd()
    if (-not $raw) { exit 0 }
    $evt = $raw | ConvertFrom-Json
    $text = ($evt.tool_input | ConvertTo-Json -Depth 8 -Compress)
    if (-not $text) { exit 0 }

    # High-confidence secret patterns only (avoid false positives)
    $patterns = @(
        'sk-ant-[A-Za-z0-9_\-]{20,}',
        'sk-or-v1-[A-Za-z0-9]{20,}',
        'gh[pousr]_[A-Za-z0-9]{30,}',
        'AKIA[0-9A-Z]{16}',
        'xox[baprs]-[A-Za-z0-9-]{10,}',
        '-----BEGIN [A-Z ]*PRIVATE KEY-----',
        '[0-9]{8,10}:[A-Za-z0-9_\-]{35}'
    )
    $hit = $null
    foreach ($p in $patterns) {
        $m = [regex]::Match($text, $p)
        if ($m.Success) { $hit = $m.Value; break }
    }
    if (-not $hit) { exit 0 }

    # Sensitive destination/context markers (ASCII substrings of vault/log/message paths)
    # Sensitive = knowledge base (.md files / vault paths) or a message. NOT infra config (.json/.env outside vault).
    $ctx = 'vault|MEMORY|decisions|Decisions-Log|_Deliverables|Telegram|message|\.md'
    if ($text -match $ctx) {
        $masked = $hit.Substring(0, [Math]::Min(6, $hit.Length)) + '***'
        [Console]::Error.WriteLine("BLOCKED by secret-guard: credential-like token ($masked) is about to be written into the knowledge base / message. Replace it with a placeholder before proceeding. (PreToolUse hook; fail-safe, never blocks non-secret ops)")
        exit 2
    }
    exit 0
} catch { exit 0 }
