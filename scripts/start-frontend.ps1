[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$frontendPath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\frontend'))
$npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npm) { throw 'Install Node.js LTS (with npm), reopen PowerShell, then run scripts\setup.ps1.' }
if (-not (Test-Path -LiteralPath (Join-Path $frontendPath 'node_modules\vite\bin\vite.js'))) {
    throw 'Frontend dependencies are missing. Run scripts\setup.ps1 or npm.cmd --prefix frontend ci.'
}
& $npm.Source --prefix $frontendPath run dev
if ($LASTEXITCODE -ne 0) { throw 'Frontend stopped with an error. Check the output above; Vite reports configuration errors or an occupied FRONTEND_PORT.' }
