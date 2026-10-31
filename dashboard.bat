@echo off
setlocal
cd /d "%~dp0"
echo ===================================================
echo   Launching MaintainerOps Interactive Web Dashboard
echo ===================================================
call maintainerops.bat dashboard --target tests/fixtures/enterprise_repo.json
pause
