# acceptance-gate.ps1 — Stop-хук «босса» для ноутбука (Windows / PowerShell).
#
# Живёт в tools/ рядом с checks.py. Руками надо сделать ровно одно —
# зарегистрировать его в settings.json (см. README.md рядом).
#
# Грабли PowerShell 5.1: файл обязан быть UTF-8 С BOM, иначе кириллица
# читается как cp1251.
#
# Режим: report-only. Никогда не блокирует остановку сессии, всегда exit 0.
# Выключить: создать файл ~\.claude\.acceptance-gate-off

$ErrorActionPreference = 'SilentlyContinue'

# Каталог стека и корень vault — из окружения, с умолчаниями ~\.claude и ~\vault
$Stack       = if ($env:CLAUDE_HOME) { $env:CLAUDE_HOME } else { Join-Path $HOME '.claude' }
$Vault       = if ($env:VAULT_ROOT)  { $env:VAULT_ROOT }  else { Join-Path $HOME 'vault' }
$RunsActive  = Join-Path $Vault '_orchestr\_ACTIVE'
$Log         = Join-Path $Stack 'acceptance-gate.log'
$Lock        = Join-Path $Stack '.acceptance-gate.lock'
$Off         = Join-Path $Stack '.acceptance-gate-off'
$Checks      = Join-Path $Stack 'tools\acceptance-gate\checks.py'
$TimeoutSec  = 900

function Write-GateLog($msg) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $msg" | Out-File -FilePath $Log -Append -Encoding utf8
}

# --- Защита 1: маркер в окружении (приёмщик не вызывает сам себя)
if ($env:ACCEPTANCE_GATE -eq '1') { exit 0 }

# --- Защита 2: stop_hook_active из полезной нагрузки хука
$payload = [Console]::In.ReadToEnd()
if ($payload -match '"stop_hook_active"\s*:\s*true') { exit 0 }

# --- Защита 3: файл-замок (протухший старше часа снимаем)
if (Test-Path $Lock) {
    $age = (Get-Date) - (Get-Item $Lock).LastWriteTime
    if ($age.TotalMinutes -gt 60) { Remove-Item $Lock -Force; Write-GateLog 'снят протухший замок' }
    else { exit 0 }
}

# --- Ручной выключатель и предусловия
if (Test-Path $Off) { exit 0 }
if (-not (Test-Path $Checks)) { exit 0 }
if (-not (Test-Path $RunsActive)) { exit 0 }
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) { exit 0 }

# Python на ноуте может называться по-разному
$py = $null
foreach ($cand in @('python3', 'python', 'py')) {
    if (Get-Command $cand -ErrorAction SilentlyContinue) { $py = $cand; break }
}
if (-not $py) { exit 0 }

# --- Условие срабатывания: закрытый прогон без секции приёмки, свежее суток
$target = Get-ChildItem -Path $RunsActive -Filter 'run-*.md' -File |
    Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-1) } |
    Sort-Object LastWriteTime -Descending |
    Where-Object {
        $t = Get-Content $_.FullName -Raw
        ($t -match '(?m)^status:\s*done\s*$') -and ($t -notmatch '(?m)^## Приёмка')
    } | Select-Object -First 1

if ($null -eq $target) {
    if ($env:ACCEPTANCE_GATE_DRYRUN -eq '1') { Write-Output 'DRY-RUN: подходящего прогона нет' }
    exit 0
}

if ($env:ACCEPTANCE_GATE_DRYRUN -eq '1') {
    Write-Output "DRY-RUN: запустил бы приёмку на $($target.FullName)"
    exit 0
}

# --- Запуск фоном, с таймаутом
New-Item -ItemType File -Path $Lock -Force | Out-Null
Write-GateLog "приёмка запускается: $($target.Name)"

$prompt = @"
Прими прогон. run-лог: $($target.FullName)
Режим: report-only — только допиши секцию '## Приёмка' в этот run-лог, ничего не чини и не переписывай.
Начни с детерминированной части: $py "$Checks" "$($target.FullName)" --json
"@

Start-Job -ScriptBlock {
    param($prompt, $log, $lock, $timeoutSec, $name)
    $env:ACCEPTANCE_GATE = '1'
    $p = Start-Process -FilePath 'claude' -PassThru -NoNewWindow -RedirectStandardOutput $log -ArgumentList @(
        '-p', '--agent', 'acceptance-gate', '--permission-mode', 'acceptEdits',
        '--allowedTools', 'Read', 'Glob', 'Grep', 'Edit', 'Bash(python3 *)',
        $prompt
    )
    if (-not $p.WaitForExit($timeoutSec * 1000)) {
        $p.Kill()
        "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  приёмка оборвана по таймауту ${timeoutSec}s: $name" |
            Out-File -FilePath $log -Append -Encoding utf8
    }
    Remove-Item $lock -Force -ErrorAction SilentlyContinue
} -ArgumentList $prompt, $Log, $Lock, $TimeoutSec, $target.Name | Out-Null

# report-only: остановку сессии не блокируем никогда
exit 0
