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

if "%~1"=="" (
    "%PYTHON_EXE%" -m maintainerops.cli --help
) else (
    "%PYTHON_EXE%" -m maintainerops.cli %*
)
