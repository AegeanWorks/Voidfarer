@echo off
setlocal EnableDelayedExpansion
title VoidFarer - Deep Space Simulator

:: Ensure we run from the project root directory
cd /d "%~dp0"
set "PYTHONPATH=%~dp0"

:: -------------------------------------------------------------
:: Detect Python executable
:: -------------------------------------------------------------
set "PYTHON_EXE="

:: 1. Check Python Launcher (py)
where py >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    py -3 -c "import sys" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set "PYTHON_EXE=py -3"
        goto :python_found
    )
)

:: 2. Check standard 'python' in PATH
where python >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    python -c "import sys" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set "PYTHON_EXE=python"
        goto :python_found
    )
)

:: 3. Check 'python3' in PATH
where python3 >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    python3 -c "import sys" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set "PYTHON_EXE=python3"
        goto :python_found
    )
)

:: 4. Check known Windows installation directories
for %%D in (
    "C:\Python314\python.exe"
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
) do (
    if exist "%%~D" (
        set "PYTHON_EXE=%%~D"
        goto :python_found
    )
)

:python_not_found
echo ========================================================================
echo [ERROR] Python 3.10+ was not found on your system!
echo.
echo Why: VoidFarer requires Python standard library (no pip packages needed).
echo Fix: Install Python from https://www.python.org/downloads/
echo      or Windows Store, and ensure "Add python.exe to PATH" is checked.
echo ========================================================================
pause
exit /b 1

:python_found
:: If command-line arguments are provided, forward them directly to CLI
if not "%~1"=="" (
    %PYTHON_EXE% -m voidfarer.cli %*
    exit /b !ERRORLEVEL!
)

:: -------------------------------------------------------------
:: Interactive 1-Click Game Launcher Menu
:: -------------------------------------------------------------
:menu
cls
echo ========================================================================
echo    __      __ _____  _____  _____   ______        _____   ______  _____  
echo    \ \    / // ___ \^|_   _^|^|  __ \ ^|  ____/\     ^|  __ \ ^|  ____^|^|  __ \ 
echo     \ \  / /^| ^|   ^| ^| ^| ^|  ^| ^|  ^| ^|^| ^|__ /  \    ^| ^|__) ^|^| ^|__   ^| ^|__) ^|
echo      \ \/ / ^| ^|   ^| ^| ^| ^|  ^| ^|  ^| ^|^|  __/ /\ \   ^|  _  / ^|  __^|  ^|  _  / 
echo       \  /  ^| ^|___^| ^|_^| ^|_ ^| ^|__^| ^|^| ^| / ____ \  ^| ^| \ \ ^| ^|____ ^| ^| \ \ 
echo        \/    \_____/^|_____^|^|_____/ ^|_^|/_/    \_\ ^|_^|  \_\^|______^|^|_^|  \_\
echo ========================================================================
echo       AUTONOMOUS DEEP-SPACE FLEET ^& HOLOGRAPHIC COCKPIT SIMULATOR
echo ========================================================================
echo.
echo   [1] Holographic Web Cockpit (Browser + Audio HUD)  [DEFAULT]
echo   [2] Interactive Terminal Cockpit REPL
echo   [3] Flagship Status ^& Commander Dossier
echo   [4] Galaxy Starmap ^& Sector Chart
echo   [5] Galactic Factions ^& Sovereign Alliances
echo   [6] Megacorporations ^& Trade Specializations
echo   [7] Run System Diagnostics ^& Automated Test Suite
echo   [0] Exit
echo.
echo ========================================================================
set "CHOICE=1"
set /p "CHOICE=Select mission mode [Press Enter for Web Cockpit]: "

if "%CHOICE%"=="1" goto :launch_web
if "%CHOICE%"=="2" goto :launch_repl
if "%CHOICE%"=="3" goto :launch_status
if "%CHOICE%"=="4" goto :launch_chart
if "%CHOICE%"=="5" goto :launch_factions
if "%CHOICE%"=="6" goto :launch_corps
if "%CHOICE%"=="7" goto :launch_tests
if "%CHOICE%"=="0" exit /b 0

:: Default to web cockpit for any unrecognized input
goto :launch_web

:launch_web
echo.
echo Launching Holographic Web Cockpit and opening browser...
%PYTHON_EXE% -m voidfarer.cli serve --open
pause
exit /b 0

:launch_repl
echo.
echo Initializing Terminal REPL Cockpit...
%PYTHON_EXE% -m voidfarer.cli repl
pause
goto :menu

:launch_status
echo.
%PYTHON_EXE% -m voidfarer.cli status
echo.
pause
goto :menu

:launch_chart
echo.
%PYTHON_EXE% -m voidfarer.cli chart
echo.
pause
goto :menu

:launch_factions
echo.
%PYTHON_EXE% -m voidfarer.cli factions
echo.
pause
goto :menu

:launch_corps
echo.
%PYTHON_EXE% -m voidfarer.cli corps
echo.
pause
goto :menu

:launch_tests
echo.
echo Running VoidFarer automated test suite...
%PYTHON_EXE% -m unittest discover -s tests
echo.
pause
goto :menu
