@echo off
rem ============================================
rem   Manga Translator - Windows launcher
rem ============================================
chcp 65001 >nul
title Manga Translator
cd /d "%~dp0"

rem Prefer Python 3.12 (more stable wheels than 3.14)
set "PY=python"
where py >nul 2>nul
if not errorlevel 1 (
    py -3.12 -c "import sys" >nul 2>nul
    if not errorlevel 1 set "PY=py -3.12"
)

:menu
cls
echo.
echo   ============================================
echo      Manga Translator     [%PY%]
echo   ============================================
echo.
echo     [1] App    - desktop window
echo     [2] Web    - browser interface, auto-restart
echo     [3] CLI    - asks for input in terminal
echo     [4] Exit
echo.
set /p "choice=  Choose [1/2/3/4]: "
if "%choice%"=="1" goto app
if "%choice%"=="2" goto web
if "%choice%"=="3" goto cli
if "%choice%"=="4" exit /b 0
goto menu

:deps
echo [i] Checking dependencies - first run may take a while...
%PY% -c "import gradio" >nul 2>nul
if errorlevel 1 %PY% -m pip install -q gradio
%PY% -c "import cv2" >nul 2>nul
if errorlevel 1 %PY% -m pip install -q opencv-python-headless pillow numpy
goto :eof

:app
call :deps
%PY% -c "import tkinter" >nul 2>nul
if errorlevel 1 (
    echo [X] tkinter not available. Use option 2 - Web - instead.
    pause
    goto menu
)
%PY% manga_app.py --desktop
echo.
pause
goto menu

:web
call :deps
echo [i] Web UI on http://127.0.0.1:7860
echo [i] Auto-restart active - Ctrl+C twice to stop fully
:webloop
%PY% -u manga_app.py --web
echo [!] Server exited - restart in 3 seconds...
timeout /t 3 >nul
goto webloop

:cli
call :deps
%PY% manga_app.py --cli
echo.
pause
goto menu
