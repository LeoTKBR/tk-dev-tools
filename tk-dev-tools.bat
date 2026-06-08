@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"

set "REPO_OWNER=LeoTKBR"
set "REPO_NAME=tk-dev-tools"
set "REPO_URL=https://github.com/%REPO_OWNER%/%REPO_NAME%"
set "BRANCH=main"
set "API_URL=https://api.github.com/repos/%REPO_OWNER%/%REPO_NAME%/commits/%BRANCH%"
set "ZIP_URL=https://github.com/%REPO_OWNER%/%REPO_NAME%/archive/refs/heads/%BRANCH%.zip"
set "TMP_ROOT=%TEMP%\tk-dev-tools-bootstrap"
set "ZIP_FILE=%TMP_ROOT%\repo.zip"
set "EXTRACT_DIR=%TMP_ROOT%\extract"
set "SOURCE_DIR="
set "STATE_FILE=%~dp0.repo-sha"
set "REQUIRED_FILES=launcher.py bootstrap_ui.py dependency_bootstrap.py qt_ui.py core_types.py dat_core.py generation_core.py spr_core.py icon.png loading.png"

call :PrintHeader
call :EnsureRepositoryFiles || goto :fail
call :EnsurePythonRuntime || goto :fail

echo.
echo Launching TK Dev Tools...
python launcher.py
if errorlevel 1 (
    echo.
    echo TK Dev Tools exited with an error.
    pause
)

endlocal
exit /b 0

:PrintHeader
echo ==================================================
echo   TK Dev Tools Bootstrap
echo ==================================================
echo Repository: %REPO_URL%
echo.
exit /b 0

:EnsureRepositoryFiles
call :GetRemoteCommit REMOTE_SHA
if errorlevel 1 exit /b 1

call :GetLocalCommit LOCAL_SHA
if errorlevel 1 set "LOCAL_SHA="

call :CheckRequiredFiles
if errorlevel 1 set "FILES_OK=0"
if errorlevel 1 (
    echo Missing files detected. Updating repository...
) else (
    set "FILES_OK=1"
)

if /i "!LOCAL_SHA!"=="!REMOTE_SHA!" if "!FILES_OK!"=="1" (
    echo Repository is up to date.
    exit /b 0
)

echo Updating repository from GitHub...

if exist "%TMP_ROOT%" rmdir /s /q "%TMP_ROOT%"
mkdir "%TMP_ROOT%" >nul 2>&1

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -UseBasicParsing -Uri '%ZIP_URL%' -OutFile '%ZIP_FILE%'; Expand-Archive -Path '%ZIP_FILE%' -DestinationPath '%EXTRACT_DIR%' -Force"
if errorlevel 1 (
    echo Failed to download or extract the repository.
    exit /b 1
)

for /d %%D in ("%EXTRACT_DIR%\%REPO_NAME%-*") do set "SOURCE_DIR=%%~fD"

if not defined SOURCE_DIR (
    echo Could not locate the extracted repository folder.
    exit /b 1
)

robocopy "%SOURCE_DIR%" "%~dp0" /E /NFL /NDL /NJH /NJS /NC /NS /NP >nul
if errorlevel 8 (
    echo Failed to copy repository files into place.
    exit /b 1
)

> "%STATE_FILE%" echo %REMOTE_SHA%
echo Repository updated successfully.
exit /b 0

:CheckRequiredFiles
set "FILES_OK=1"
for %%F in (%REQUIRED_FILES%) do (
    if not exist "%~dp0%%F" (
        set "FILES_OK=0"
        exit /b 1
    )
)
exit /b 0

:GetRemoteCommit
set "%~1="
for /f "usebackq delims=" %%I in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "(Invoke-RestMethod -Headers @{ 'User-Agent' = 'tk-dev-tools-bootstrap' } -Uri '%API_URL%').sha"`) do (
    set "%~1=%%I"
)
if not defined %~1 (
    echo Failed to read the latest repository commit from GitHub.
    exit /b 1
)
exit /b 0

:GetLocalCommit
set "%~1="
if exist "%STATE_FILE%" (
    set /p "%~1="<"%STATE_FILE%"
)
exit /b 0

:EnsurePythonRuntime
python --version >nul 2>&1
if not errorlevel 1 exit /b 0

py --version >nul 2>&1
if not errorlevel 1 exit /b 0

where winget >nul 2>&1
if errorlevel 1 (
    echo Python is not installed and WinGet is not available.
    echo Please install Python manually from https://www.python.org/downloads/
    exit /b 1
)

echo Python is not installed.
echo Installing the latest Python runtime manager through WinGet...
winget install 9NQ7512CXL7T -e --silent --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
    echo Failed to install the Python runtime manager.
    exit /b 1
)

python --version >nul 2>&1
if not errorlevel 1 exit /b 0

py --version >nul 2>&1
if not errorlevel 1 exit /b 0

echo Python is still unavailable after installation.
echo Open a new terminal and try again.
exit /b 1

:fail
echo.
echo Bootstrap failed.
pause
endlocal
exit /b 1
