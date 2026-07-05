@echo off
rem exam_scribe launcher (ASCII + CRLF, encoding-safe)
cd /d "%~dp0"
python -c "import pyhwpx" 2>nul || pip install pyhwpx
python main.py
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to launch. Check: Python installed, Hangul^(HWP^) available, main.py in this folder.
    pause
)
