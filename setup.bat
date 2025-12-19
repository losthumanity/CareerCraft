@echo off
REM Setup script for Job Sniper
echo ========================================
echo Job Sniper - Initial Setup
echo ========================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://www.python.org/
    pause
    exit /b 1
)

echo [1/5] Python detected
python --version

REM Create virtual environment
echo.
echo [2/5] Creating virtual environment...
if exist venv (
    echo Virtual environment already exists
) else (
    python -m venv venv
    echo Virtual environment created
)

REM Activate and install dependencies
echo.
echo [3/5] Installing dependencies...
call venv\Scripts\activate
pip install -r requirements.txt

REM Create necessary directories
echo.
echo [4/5] Creating directories...
if not exist logs mkdir logs
if not exist data mkdir data
if not exist output mkdir output
if not exist templates mkdir templates
if not exist tailored_resumes mkdir tailored_resumes
if not exist tailor mkdir tailor

REM Create .env file from example
echo.
echo [5/5] Setting up configuration...
if not exist .env (
    copy .env.example .env
    echo .env file created - PLEASE EDIT IT WITH YOUR API KEYS
) else (
    echo .env file already exists
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next Steps:
echo 1. Edit .env file with your API keys:
echo    - DISCORD_WEBHOOK_URL (for notifications)
echo    - GEMINI_API_KEY (for resume tailoring)
echo 2. Edit tailor/tailor_config.yaml with your resume data
echo 3. Run: venv\Scripts\activate
echo 4. Test watcher: python watcher/smart_watcher_v2.py
echo 5. Test tailor: python tailor/test_tailor.py
echo 6. Launch dashboard: streamlit run dashboard/dashboard.py
echo.
echo Phase 2 (Resume Tailor) is now ready!
echo.
pause
