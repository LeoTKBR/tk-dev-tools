@echo off
setlocal EnableExtensions

rem TK Dev Tools installer/launcher
rem This script installs the bundled release to %LOCALAPPDATA%\TKDevTools\app
rem and then starts the installed executable.

set "SCRIPT_DIR=%~dp0"
set "INSTALL_ROOT=%LOCALAPPDATA%\TKDevTools"
set "INSTALL_DIR=%INSTALL_ROOT%\app"
set "BUNDLE_DIR="

if exist "%SCRIPT_DIR%TKDevTools.exe" (
    set "BUNDLE_DIR=%SCRIPT_DIR%"
) else if exist "%SCRIPT_DIR%dist\TKDevTools\TKDevTools.exe" (
    set "BUNDLE_DIR=%SCRIPT_DIR%dist\TKDevTools"
)

if not exist "%INSTALL_ROOT%" mkdir "%INSTALL_ROOT%" >nul 2>&1

if defined BUNDLE_DIR (
    echo Installing or updating TK Dev Tools...
    robocopy "%BUNDLE_DIR%" "%INSTALL_DIR%" /MIR /NFL /NDL /NJH /NJS /NP /R:2 /W:1 >nul
    if errorlevel 8 (
        echo Failed to copy the application files.
        exit /b 1
    )
) else (
    echo Installed bundle not found in this folder.
    if not exist "%INSTALL_DIR%\TKDevTools.exe" (
        echo Could not find a local installation to launch.
        exit /b 1
    )
)

if not exist "%INSTALL_DIR%\TKDevTools.exe" (
    echo Installed executable not found.
    exit /b 1
)

start "" "%INSTALL_DIR%\TKDevTools.exe"
exit /b 0
