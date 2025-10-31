@echo off
REM Setup script for Piu Testing
REM Run this script to install dependencies and run tests

echo ========================================
echo   Piu Testing Setup
echo ========================================
echo.

echo [1/4] Checking Python version...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python not found! Please install Python first.
    pause
    exit /b 1
)

echo.
echo [2/4] Installing pytest and dependencies...
pip install pytest pytest-cov pytest-timeout pytest-mock

if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies!
    pause
    exit /b 1
)

echo.
echo [3/4] Verifying installation...
pytest --version

echo.
echo [4/4] Running basic tests...
pytest tests/integration/test_services_init.py -v

echo.
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo Next steps:
echo   1. Run: pytest -v              (all tests)
echo   2. Run: pytest -v -m integration  (integration tests only)
echo   3. Run: pytest --cov=services  (with coverage)
echo.
pause

