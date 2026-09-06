# Orchestrator stack for Claude Code. Author: @kamil_ibrgmv - https://instagram.com/kamil_ibrgmv
# Payload is read by the shared runner from [Console]::OpenStandardInput().
& (Join-Path $PSScriptRoot 'run-guard.ps1') -Kind secret
exit $LASTEXITCODE
