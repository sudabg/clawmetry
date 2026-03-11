@echo off
chcp 65001 >nul 2>&1
REM ClawMetry Installer for Windows (CMD)
REM Usage: curl -fsSL https://clawmetry.com/install.cmd -o install.cmd && install.cmd && del install.cmd

echo.
echo   ClawMetry [claw] Installer
echo   Real-time observability for OpenClaw agents
echo.

REM Check for Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    where python3 >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo   [ERROR] Python not found.
        echo   Install Python from https://python.org/downloads
        echo   Make sure to check "Add Python to PATH" during install.
        echo.
        exit /b 1
    )
    set PYTHON=python3
) else (
    set PYTHON=python
)

REM Check Python version
%PYTHON% -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo   [ERROR] Python 3.10+ required.
    echo   Install from https://python.org/downloads
    exit /b 1
)

echo   [..] Installing clawmetry...
%PYTHON% -m pip install --upgrade clawmetry >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    %PYTHON% -m pip install --user --upgrade clawmetry >nul 2>&1
)
echo   [OK] ClawMetry installed
echo.

REM Run onboarding
clawmetry onboard
