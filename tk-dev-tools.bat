@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set "PY_CMD="
where python >nul 2>&1
if not errorlevel 1 set "PY_CMD=python"

if not defined PY_CMD (
    where py >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py -3"
)

if not defined PY_CMD (
    where winget >nul 2>&1
    if errorlevel 1 (
        echo Python is not installed and WinGet is not available.
        echo Please install Python manually from https://www.python.org/downloads/
        pause
        exit /b 1
    )

    echo Python is not installed.
    echo Installing the latest Python runtime through WinGet...
    winget install 9NQ7512CXL7T -e --silent --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo Failed to install the Python runtime manager.
        pause
        exit /b 1
    )

    timeout /t 2 >nul

    where python >nul 2>&1
    if not errorlevel 1 set "PY_CMD=python"

    if not defined PY_CMD (
        where py >nul 2>&1
        if not errorlevel 1 set "PY_CMD=py -3"
    )
)

if not defined PY_CMD (
    echo Python is still unavailable after installation.
    echo Open a new terminal and try again.
    pause
    exit /b 1
)

echo Launching TK Dev Tools...
%PY_CMD% launcher.py
if errorlevel 1 (
    echo.
    echo TK Dev Tools exited with an error.
    pause
)

endlocal
