@echo off
echo [1/2] Installing dependencies...
pip install pystray Pillow pyinstaller --quiet
if errorlevel 1 (
    echo [ERROR] pip install failed. Check your Python/pip environment.
    pause
    exit /b 1
)

echo [2/2] Running build script...
python build.py
if errorlevel 1 (
    pause
    exit /b 1
)
pause
