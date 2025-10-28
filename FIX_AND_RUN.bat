@echo off
echo ========================================
echo Fixing and Running Piu...
echo ========================================

REM Kill any Python processes
echo [1/3] Checking for old processes...
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul

REM Verify logo files exist
echo [2/3] Checking logo files...
if exist logo_Piu.ico (
    echo [OK] logo_Piu.ico found
) else (
    echo [ERROR] logo_Piu.ico NOT found!
    pause
    exit
)

if exist logo_Piu_resized.png (
    echo [OK] logo_Piu_resized.png found
) else (
    echo [ERROR] logo_Piu_resized.png NOT found!
    pause
    exit
)

REM Run Piu
echo [3/3] Starting Piu...
echo.
python Piu.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application failed to start
    pause
)

