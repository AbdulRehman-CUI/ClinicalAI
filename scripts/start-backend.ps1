[CmdletBinding()]
param([switch]$NoReload)

$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Missing .venv. Run scripts\setup.ps1 first.' }

$configurationJson = & $python (Join-Path $PSScriptRoot 'check_environment.py') --json
if ($LASTEXITCODE -ne 0) { throw 'Backend preflight failed. Correct the configuration or run scripts\setup.ps1 -RecreateVenv.' }
$configuration = $configurationJson | ConvertFrom-Json
if (-not $configuration.ai_configured) {
    Write-Warning "$($configuration.ai_provider) credentials are not configured. Authentication and patient records work; AI analysis requires the selected provider's API key in .env."
}
$backendPath = Join-Path $projectRoot 'backend'
$uvicornArgs = @('-m', 'uvicorn', 'app.main:app', '--app-dir', $backendPath, '--host', $configuration.host, '--port', [string]$configuration.port)
if (-not $NoReload) { $uvicornArgs += @('--reload', '--reload-dir', $backendPath) }
Write-Host "Starting ClinicalAI backend on $($configuration.host):$($configuration.port). Press Ctrl+C to stop."
& $python @uvicornArgs
if ($LASTEXITCODE -ne 0) { throw 'Backend stopped with an error. Check the output above; if the port is in use, stop that server or change BACKEND_PORT in .env.' }
