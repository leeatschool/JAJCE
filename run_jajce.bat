@echo off
setlocal
cd /d "%~dp0"

REM If arguments were passed (e.g. files dragged onto the .bat file), pass them to main.py
if "%~1"=="" (
    start "" pythonw main.py
) else (
    python main.py %*
)
endlocal
