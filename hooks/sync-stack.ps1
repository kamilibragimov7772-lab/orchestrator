# sync-stack.ps1 -- two-way bridge for the Claude Code stack
# Laptop  <->  bare repo on your server (<user>@<server>:<path-to-bare-repo>)
# One-time setup: cd ~/.claude; git init; git remote add origin <user>@<server>:<path-to-bare-repo>
#
# Scope: agents, commands, skills, orchestrator protocol, CLAUDE.md.
# Secrets/transcripts/caches are excluded by the whitelist in ~/.claude/.gitignore.
#
# Runs from the Stop hook after every session. Must NEVER block the session:
# no network / server down / VPN off  ->  log and exit 0 quietly.
#
# NOTE: keep this file ASCII-only. PowerShell 5.1 mangles Cyrillic in .ps1.

$ErrorActionPreference = 'SilentlyContinue'

$stack = Join-Path $env:USERPROFILE '.claude'
$log   = Join-Path $stack 'sync-stack.log'

function Write-Log($msg) {
    $line = "{0}  {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg
    Add-Content -Path $log -Value $line -Encoding utf8
}

# Keep the log small
if ((Test-Path $log) -and ((Get-Item $log).Length -gt 200KB)) {
    Get-Content $log -Tail 300 | Set-Content $log -Encoding utf8
}

Set-Location $stack
if (-not (Test-Path (Join-Path $stack '.git'))) { Write-Log 'SKIP: not a git repo'; exit 0 }

# Two callers now run this script: the Stop hook (after a session) and the
# scheduled task ClaudeStackBridge (logon + every 10 min). If they overlap,
# git dies on index.lock and the log fills with scary false alarms. Skip instead.
if (Test-Path (Join-Path $stack '.gitindex.lock')) { Write-Log 'skip: another sync in progress'; exit 0 }

# 1. Commit local changes (if any)
git add -A 2>&1 | Out-Null
git diff --cached --quiet 2>&1 | Out-Null
$hasChanges = ($LASTEXITCODE -ne 0)

if ($hasChanges) {
    $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm'
    $commitOut = git commit -q -m "auto-sync from laptop $stamp" 2>&1
    if ($LASTEXITCODE -ne 0) {
        # Коммит может отвалиться по pre-commit хуку (agent-lint) или по конфигу git.
        # Без этой проверки лог писал 'committed' и дальше 'pushed OK' при нулевой синхронизации —
        # тихий отказ моста. Добавлено 2026-08-21 после того, как воротa нашли эту дыру.
        Write-Log "COMMIT ОТКЛОНЁН (код $LASTEXITCODE) - синхронизации НЕ БЫЛО. Причина: $commitOut"
        Write-Log 'если это agent-lint: cd ~/.claude; py -3 tools/agent-lint.py --quiet'
        exit 1
    }
    Write-Log 'committed local changes'
}

# 2. Is the server reachable? Short timeout - never hang the session.
$env:GIT_SSH_COMMAND = 'ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new'
git ls-remote --exit-code origin 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Log 'server unreachable (VPN/network?) - local commit kept, will sync next time'
    exit 0
}

# 3. Pull server-side changes, then push ours (two-way)
git pull --rebase --autostash -q origin main 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    git rebase --abort 2>&1 | Out-Null
    Write-Log 'CONFLICT on pull --rebase - manual fix needed: cd ~/.claude; git status'
    exit 0
}

git push -q origin main 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    if ($hasChanges) { Write-Log 'pushed to server OK' } else { Write-Log 'in sync (nothing to push)' }
} else {
    Write-Log 'push failed - will retry next session'
}

exit 0
