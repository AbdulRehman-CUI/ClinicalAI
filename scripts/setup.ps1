[CmdletBinding()]
param(
    [string]$Python = '',
    [switch]$RecreateVenv,
    [switch]$SkipFrontend
)

$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$venvPath = Join-Path $projectRoot '.venv'
$venvPython = Join-Path $venvPath 'Scripts\python.exe'

# Resolve the base interpreter before moving an activated or relocated environment.
$pythonArgs = @()
if ($Python) {
    $pythonCommand = $Python
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCommand = 'py'
    $pythonArgs = @('-3')
} else {
    $pythonCommand = 'python'
}
try {
    $basePython = & $pythonCommand @pythonArgs -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11 or newer is required"; print(sys._base_executable)'
    if ($LASTEXITCODE -ne 0 -or -not $basePython) { throw 'Python probe failed.' }
    $basePython = ($basePython | Select-Object -Last 1).Trim()
} catch {
    throw 'A working Python 3.11+ installation is required. Install CPython for Windows, reopen PowerShell, or run setup.ps1 -Python C:\path\to\python.exe. Do not use the broken .venv as the base interpreter.'
}

if ($RecreateVenv -and (Test-Path -LiteralPath $venvPath)) {
    if (Get-Command deactivate -ErrorAction SilentlyContinue) { deactivate }
    $backupPath = "$venvPath.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss-fff')"
    $rootPrefix = $projectRoot.TrimEnd('\') + '\'
    foreach ($target in @($venvPath, $backupPath)) {
        if (-not [IO.Path]::GetFullPath($target).StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Virtual environment paths must remain inside this checkout.'
        }
    }
    if ((Get-Item -LiteralPath $venvPath).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw 'The .venv directory is a link. Move the link manually before recreating the environment.'
    }
    try { Move-Item -LiteralPath $venvPath -Destination $backupPath }
    catch { throw 'Close backend servers and Python processes using .venv, deactivate it, then rerun setup.ps1 -RecreateVenv. No project data was deleted.' }
    Write-Host "Previous virtual environment retained at $backupPath"
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    & $basePython -m venv $venvPath
    if ($LASTEXITCODE -ne 0) { throw 'Could not create .venv. Close processes using it and check folder permissions.' }
} else {
    & $venvPython -c 'import sys; print("Using Python", sys.version.split()[0])'
    if ($LASTEXITCODE -ne 0) { throw 'The existing .venv cannot run. Rerun setup.ps1 -RecreateVenv.' }
}

& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'pip installation failed. Check network access and your Python installation.' }
& $venvPython -m pip install -r (Join-Path $projectRoot 'backend\requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed. Resolve the pip error above, then rerun setup.ps1.' }
& $venvPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Installed Python dependencies are incompatible. See pip check output above.' }

$envFile = Join-Path $projectRoot '.env'
if (-not (Test-Path -LiteralPath $envFile)) {
    Copy-Item -LiteralPath (Join-Path $projectRoot '.env.example') -Destination $envFile
    Write-Host 'Created .env from .env.example. Existing environment files are never overwritten.'
}
& $venvPython (Join-Path $PSScriptRoot 'check_environment.py')
if ($LASTEXITCODE -ne 0) { throw 'Backend configuration check failed. Correct .env and rerun setup.ps1.' }

if (-not $SkipFrontend) {
    $npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $npm) { throw 'Install Node.js LTS (with npm), reopen PowerShell, then rerun setup.ps1.' }
    & $npm.Source --prefix (Join-Path $projectRoot 'frontend') ci
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed. See npm output above.' }
}
Write-Host 'Setup complete. Run scripts\start-backend.ps1 and scripts\start-frontend.ps1 in separate PowerShell windows.'
