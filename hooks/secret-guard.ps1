# Payload is read by the shared runner from [Console]::OpenStandardInput().
& (Join-Path $PSScriptRoot 'run-guard.ps1') -Kind secret
exit $LASTEXITCODE
