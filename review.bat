@echo off
setlocal
cd /d "%~dp0"
echo ===================================================
echo   Launching MaintainerOps Interactive Review Queue
echo ===================================================
call maintainerops.bat review tests/fixtures/enterprise_repo.json
pause
