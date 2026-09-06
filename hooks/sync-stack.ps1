# Orchestrator stack for Claude Code. Author: @kamil_ibrgmv - https://instagram.com/kamil_ibrgmv
# Opt-in bridge. ASCII-only wrapper for PowerShell 5.1 and 7.
$ErrorActionPreference = 'Stop'
if ($env:ORCHESTRATOR_SYNC_ENABLED -ne '1') {
    Write-Output '{"systemMessage":"sync-stack: skipped (opt-in disabled)"}'
    exit 0
}
$stackRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $stackRoot 'tools/sync_stack.py'
try {
    if ($env:ORCHESTRATOR_PYTHON) { $pythonExe = $env:ORCHESTRATOR_PYTHON; $pythonArgs = @() }
    elseif (Get-Command python3 -ErrorAction SilentlyContinue) { $pythonExe = 'python3'; $pythonArgs = @() }
    elseif (Get-Command py -ErrorAction SilentlyContinue) { $pythonExe = 'py'; $pythonArgs = @('-3') }
    elseif (Get-Command python -ErrorAction SilentlyContinue) { $pythonExe = 'python'; $pythonArgs = @() }
    else { throw 'Python missing; sync NOT CHECKED' }
    $result = & $pythonExe @pythonArgs $scriptPath --root $stackRoot
    $code = $LASTEXITCODE
    Write-Output (@{ systemMessage = "sync-stack: $result (exit $code)" } | ConvertTo-Json -Compress)
    exit $code
} catch {
    [Console]::Error.WriteLine('sync-stack: failed; verify Python and configuration')
    exit 1
}
