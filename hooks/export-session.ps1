# Opt-in export wrapper. No destructive directory mirroring.
$ErrorActionPreference = 'Stop'
try {
    $reader = New-Object System.IO.StreamReader([Console]::OpenStandardInput(), [System.Text.Encoding]::UTF8)
    $payload = $reader.ReadToEnd()
    $OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $exportScript = Join-Path (Split-Path -Parent $PSScriptRoot) 'tools/export_session.py'
    if ($env:ORCHESTRATOR_PYTHON) { $pythonExe = $env:ORCHESTRATOR_PYTHON; $pythonArgs = @() }
    elseif (Get-Command python3 -ErrorAction SilentlyContinue) { $pythonExe = 'python3'; $pythonArgs = @() }
    elseif (Get-Command py -ErrorAction SilentlyContinue) { $pythonExe = 'py'; $pythonArgs = @('-3') }
    elseif (Get-Command python -ErrorAction SilentlyContinue) { $pythonExe = 'python'; $pythonArgs = @() }
    else { throw 'Python unavailable' }
    $payload | & $pythonExe @pythonArgs $exportScript
    exit $LASTEXITCODE
} catch {
    [Console]::Error.WriteLine('export-session: failed; verify runtime and configuration')
    exit 1
}
