$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Robocopy returns success/failure ONLY via exit code (0-7 = ok, >=8 = files failed).
# Helper reads $LASTEXITCODE so a failed sync can no longer be reported as success.
function Invoke-Mirror($src, $dst, $label) {
    robocopy $src $dst /MIR /XD node_modules .git .next dist .cache .turbo .parcel-cache .vite build .vscode /XF .DS_Store Thumbs.db /NFL /NDL /NJH /NJS /NC /NS /NP /R:1 /W:1 | Out-Null
    $code = $LASTEXITCODE
    if ($code -ge 8) { return "FAIL($label exit=$code)" } else { return "ok($label)" }
}

try {
    $raw = [Console]::In.ReadToEnd()
    $evt = $raw | ConvertFrom-Json

    # Vault root: env VAULT_ROOT, default ~\vault
    $vault = if ($env:VAULT_ROOT) { $env:VAULT_ROOT } else { Join-Path $env:USERPROFILE 'vault' }
    $logsDir = Join-Path $vault '08-Работа-Claude\_Логи'
    $workDir = Join-Path $vault '08-Работа-Claude'
    if (-not (Test-Path -LiteralPath $logsDir)) { New-Item -ItemType Directory -Path $logsDir -Force | Out-Null }

    $stamp = (Get-Date).ToString('yyyy-MM-dd_HH-mm-ss')
    $sid = if ($evt.session_id) { $evt.session_id.Substring(0, [Math]::Min(8, $evt.session_id.Length)) } else { 'nosid' }

    # 1. Export transcript
    $tpath = $evt.transcript_path
    if ($tpath -and (Test-Path -LiteralPath $tpath)) {
        $jsonlDst = Join-Path $logsDir "$stamp`_$sid.jsonl"
        Copy-Item -LiteralPath $tpath -Destination $jsonlDst -Force

        $mdDst = Join-Path $logsDir "$stamp`_$sid.md"
        $lines = Get-Content -LiteralPath $tpath -Encoding UTF8
        $md = @()
        $md += "# Claude Code session $stamp"
        $md += ""
        $md += "- session_id: $($evt.session_id)"
        $md += "- cwd: $($evt.cwd)"
        $md += "- transcript: [[$(Split-Path $jsonlDst -Leaf)]]"
        $md += ""
        $md += "---"
        $md += ""
        foreach ($l in $lines) {
            if (-not $l) { continue }
            try { $m = $l | ConvertFrom-Json } catch { continue }
            if ($m.type -eq 'user' -and $m.message.content) {
                $md += "## Пользователь"
                $md += ""
                $c = $m.message.content
                if ($c -is [string]) { $md += $c } else { foreach ($p in $c) { if ($p.type -eq 'text' -and $p.text) { $md += $p.text } } }
                $md += ""
            } elseif ($m.type -eq 'assistant' -and $m.message.content) {
                $md += "## Claude"
                $md += ""
                foreach ($p in $m.message.content) {
                    if ($p.type -eq 'text' -and $p.text) { $md += $p.text }
                    elseif ($p.type -eq 'tool_use') { $md += "`n**[tool: $($p.name)]**`n" }
                }
                $md += ""
            }
        }
        $md -join "`n" | Out-File -LiteralPath $mdDst -Encoding UTF8
    }

    # 2. Mirror project working folders into the vault (<VAULT_ROOT>\08-Работа-Claude\<leaf name>).
    #    Заполни свои папки: каждая строка — абсолютный путь к рабочей папке проекта.
    #    Строки-заглушки в угловых скобках пропускаются.
    $projectFolders = @(
        '<project-folder-1>',
        '<project-folder-2>'
    )
    $syncStatus = @()
    foreach ($src in $projectFolders) {
        if ($src -like '<*>') { continue }
        $name = Split-Path $src -Leaf
        if (Test-Path -LiteralPath $src) {
            $syncStatus += Invoke-Mirror $src (Join-Path $workDir $name) $name
        } else { $syncStatus += "skip(${name}: source missing)" }
    }

    # 3. Persist result to a log (hook is async; systemMessage alone is ephemeral)
    $logLine = "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) sid=$sid sync=[$($syncStatus -join ', ')]"
    try { Add-Content -LiteralPath (Join-Path $logsDir '_hook.log') -Value $logLine -Encoding UTF8 } catch {}

    # 3.5 Orchestrator index reconciliation (ENFORCEMENT: runs every session end,
    # self-heals 00_runs_index.md count even if orchestrator skipped Step 8/9).
    try {
        $orchDir = Join-Path $vault '_orchestr'
        $archDir = Join-Path $orchDir '_ARCHIVE'
        $idxFile = Join-Path $orchDir '00_runs_index.md'
        if ((Test-Path -LiteralPath $archDir) -and (Test-Path -LiteralPath $idxFile)) {
            $runs = Get-ChildItem -LiteralPath $archDir -Filter 'run-*.md' -ErrorAction SilentlyContinue
            $idx = Get-Content -LiteralPath $idxFile -Encoding UTF8 -Raw
            $missing = @()
            foreach ($r in $runs) {
                $base = $r.BaseName
                if ($idx -notmatch [regex]::Escape($base)) { $missing += $base }
            }
            if ($missing.Count -gt 0) {
                $block = @('', ('## Auto-reconciled (hook) ' + (Get-Date -Format 'yyyy-MM-dd HH:mm')), '')
                foreach ($mname in $missing) { $block += "- [[$mname]]" }
                Add-Content -LiteralPath $idxFile -Value ($block -join "`n") -Encoding UTF8
                $syncStatus += "index-reconciled(+$($missing.Count))"
            }
        }
    } catch {}

    $failed = @($syncStatus | Where-Object { $_ -like 'FAIL*' })
    if ($failed.Count -gt 0) {
        Write-Output (@{ systemMessage = "ВНИМАНИЕ: синхронизация частично не удалась: $($failed -join ', '). Лог: 08-Работа-Claude\_Логи\_hook.log" } | ConvertTo-Json -Compress)
    } else {
        Write-Output (@{ systemMessage = "Сессия и рабочие папки синхронизированы ($($syncStatus -join ', '))" } | ConvertTo-Json -Compress)
    }
} catch {
    Write-Output (@{ systemMessage = "export-session hook error: $($_.Exception.Message)" } | ConvertTo-Json -Compress)
}
