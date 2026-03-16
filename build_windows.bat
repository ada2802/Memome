@echo off
REM ============================================================
REM  MemoMe — Windows build script
REM  Run this from the memome_v2 project root on a Windows machine
REM  with Python + all dependencies already installed.
REM
REM  Output: installer\MemoMe-v3.0-windows-setup.exe
REM ============================================================

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   MemoMe Windows Build
echo ============================================================
echo.

REM ── Check prerequisites ──────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ and add it to PATH.
    pause & exit /b 1
)

where pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

pip show pystray >nul 2>&1
if errorlevel 1 (
    echo Installing pystray + Pillow...
    pip install pystray pillow
)

pip show pywin32 >nul 2>&1
if errorlevel 1 (
    echo Installing pywin32 (needed for Windows tray icon)...
    pip install pywin32
)

REM ── Create assets folder + placeholder icon if none exists ───
if not exist "assets" mkdir assets

if not exist "assets\icon.ico" (
    echo NOTE: No assets\icon.ico found.
    echo       Using PyInstaller default icon.
    echo       Replace assets\icon.ico with a 256x256 ICO file for a branded installer.
)

REM ── Clean previous build ─────────────────────────────────────
echo.
echo Cleaning previous build...
if exist "dist\MemoMe" rmdir /s /q "dist\MemoMe"
if exist "build"       rmdir /s /q "build"

REM ── Run PyInstaller ──────────────────────────────────────────
echo.
echo Running PyInstaller (this takes 3-8 minutes)...
echo.
pyinstaller MemoMe.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller failed. Check output above.
    pause & exit /b 1
)

echo.
echo PyInstaller done. Bundle at: dist\MemoMe\

REM ── Build Inno Setup installer ───────────────────────────────
echo.
set INNO_PATH=
for %%p in (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    "C:\Program Files\Inno Setup 6\ISCC.exe"
) do (
    if exist %%p set INNO_PATH=%%p
)

if "!INNO_PATH!"=="" (
    echo Inno Setup not found. Skipping installer creation.
    echo.
    echo To create an installer:
    echo   1. Download Inno Setup from https://jrsoftware.org/isinfo.php
    echo   2. Re-run this script, or open installer.iss manually.
    echo.
    echo Your raw bundle is ready at:  dist\MemoMe\
    echo You can zip that folder and share it as a portable build.
    goto :done
)

echo Building installer with Inno Setup...
if not exist "installer" mkdir installer
!INNO_PATH! installer.iss
if errorlevel 1 (
    echo ERROR: Inno Setup compilation failed.
    pause & exit /b 1
)

:done
echo.
echo ============================================================
echo   BUILD COMPLETE
echo ============================================================
echo.
if exist "installer\MemoMe-v3.0-windows-setup.exe" (
    echo   Installer: installer\MemoMe-v3.0-windows-setup.exe
    for %%F in ("installer\MemoMe-v3.0-windows-setup.exe") do echo   Size:      %%~zF bytes
) else (
    echo   Bundle:    dist\MemoMe\
)
echo.
echo   Upload to GitHub Releases as:
echo   MemoMe-v3.0-windows-setup.exe
echo.
pause
