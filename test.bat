@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\bin\python.exe" (
    set "PYTHON_EXE=.venv\bin\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo ===================================================
echo   Running MaintainerOps Automated Test Suite
echo ===================================================
"%PYTHON_EXE%" -m pytest -v
echo ===================================================
pause
