# Shared ASCII wrapper; payload stays on stdin. No persistent logs containing commands.
param([Parameter(Mandatory=$true)][ValidateSet('secret','risk')][string]$Kind)
$ErrorActionPreference = 'Stop'
try {
    $reader = New-Object System.IO.StreamReader([Console]::OpenStandardInput(), [System.Text.Encoding]::UTF8)
    $payload = $reader.ReadToEnd()
    $OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $guardScript = Join-Path (Split-Path -Parent $PSScriptRoot) 'tools/guard.py'
    if ($env:ORCHESTRATOR_PYTHON) { $pythonExe = $env:ORCHESTRATOR_PYTHON; $pythonArgs = @() }
    elseif (Get-Command python3 -ErrorAction SilentlyContinue) { $pythonExe = 'python3'; $pythonArgs = @() }
    elseif (Get-Command py -ErrorAction SilentlyContinue) { $pythonExe = 'py'; $pythonArgs = @('-3') }
    elseif (Get-Command python -ErrorAction SilentlyContinue) { $pythonExe = 'python'; $pythonArgs = @() }
    else { throw 'Python unavailable' }
    $payload | & $pythonExe @pythonArgs $guardScript $Kind
    exit $LASTEXITCODE
} catch {
    [Console]::Error.WriteLine("$Kind-guard: runtime failure; operation NOT CHECKED and blocked")
    exit 2
}
