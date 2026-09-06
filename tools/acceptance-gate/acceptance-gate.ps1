# Report-only worker; configure async at the HOST, never with Start-Job.
$ErrorActionPreference = 'Stop'
try {
    $worker = Join-Path $PSScriptRoot 'launch.py'
    if ($env:ORCHESTRATOR_PYTHON) { $pythonExe = $env:ORCHESTRATOR_PYTHON; $pythonArgs = @() }
    elseif (Get-Command python3 -ErrorAction SilentlyContinue) { $pythonExe = 'python3'; $pythonArgs = @() }
    elseif (Get-Command py -ErrorAction SilentlyContinue) { $pythonExe = 'py'; $pythonArgs = @('-3') }
    elseif (Get-Command python -ErrorAction SilentlyContinue) { $pythonExe = 'python'; $pythonArgs = @() }
    else { throw 'Python unavailable' }
    $workerArgs = @()
    if ($env:ACCEPTANCE_GATE_DRYRUN -eq '1') { $workerArgs += '--dry-run' }
    & $pythonExe @pythonArgs $worker @workerArgs
    exit $LASTEXITCODE
} catch {
    [Console]::Error.WriteLine('acceptance-gate: failed; verify runtime and configuration')
    exit 1
}
