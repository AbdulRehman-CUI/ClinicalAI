@echo off
setlocal
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"
if not exist .env (
  copy .env.example .env >nul
)
if exist docker-compose.yml (
  docker compose up --build
) else (
  echo docker-compose.yml not found.
  exit /b 1
)
