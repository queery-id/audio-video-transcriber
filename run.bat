@echo off
@chcp 65001 >nul
setlocal
title Audio ^& Video Transcriber
cd /d "%~dp0"

set PYTHON=.venv\Scripts\python.exe

:: Check for virtual environment
if not exist .venv (
    echo 🔧 First run detected. Setting up environment...
    python -m venv .venv
    echo 📦 Installing dependencies...
    %PYTHON% -m pip install -r requirements.txt
    echo ✅ Setup complete!
    echo.
)

:: Verify venv python exists
if not exist %PYTHON% (
    echo ❌ Error: Virtual environment Python not found at %PYTHON%
    echo    Try deleting .venv folder and run this script again.
    pause
    goto :eof
)

:: Check if arguments were passed (Drag & Drop)
if "%~1" neq "" (
    echo 📁 Processing dropped files...
    %PYTHON% src\main.py %*
    echo.
    echo ✅ Done!
    pause
    goto :eof
)

:: Interactive Mode (Double Click)
cls
echo ========================================================
echo 🎧🎬 Audio ^& Video Transcriber (Gemini 2.0)
echo ========================================================
echo.
echo Usage Options:
echo  1. Drag and drop audio/video files onto this icon
echo  2. Type the file path below
echo.
echo Supported formats: MP4, MKV, AVI, MP3, WAV, FLAC, M4A...
echo.

if not exist "input" mkdir input
if not exist "output" mkdir output

:ask
echo Options:
echo [F] Enter specific file path
echo [I] Process all files in 'input' folder
echo [T] Translate all files in 'input' folder to Indonesian
echo [B] Bilingual (Original + Indo) for all files in 'input' folder
echo [Q] Quit
echo.
set /p "choice=Select option: "

if /i "%choice%"=="Q" goto :eof
if /i "%choice%"=="I" (
    echo 📂 Processing files in 'input' folder...
    %PYTHON% src\main.py input --output-dir output
    echo.
    echo ✅ Batch processing complete! Output saved to 'output' folder.
    pause
    goto :ask
)
if /i "%choice%"=="T" (
    echo 📂 Translating files in 'input' folder to Indonesian...
    %PYTHON% src\main.py input --output-dir output --translate id
    echo.
    echo ✅ Translation complete! Output saved to 'output' folder.
    pause
    goto :ask
)
if /i "%choice%"=="B" (
    echo 📂 Generating Bilingual Subtitles ^(Original + Indonesian^)...
    %PYTHON% src\main.py input --output-dir output --translate id --bilingual
    echo.
    echo ✅ Bilingual processing complete! Output saved to 'output' folder.
    pause
    goto :ask
)

set /p "file=Enter file/folder path: "
if "%file%"=="" goto :ask

echo.
echo Select Output Mode:
echo [1] Transcribe Only (Default)
echo [2] Translate to Indonesian
echo [3] Bilingual (Original + Indonesian)
set "mode=1"
set /p "mode=Select mode (Enter=1): "

echo.
set "CMD_ARGS=--output-dir output"
if "%mode%"=="2" set "CMD_ARGS=--output-dir output --translate id"
if "%mode%"=="3" set "CMD_ARGS=--output-dir output --translate id --bilingual"

%PYTHON% src\main.py "%file%" %CMD_ARGS%

echo.
pause
goto :ask
