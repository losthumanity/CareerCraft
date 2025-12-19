@echo off
REM Resume Tailor Launcher
REM Runs the resume tailor in interactive mode

echo ====================================
echo    JOBIFY - RESUME TAILOR
echo ====================================
echo.

REM Check if virtual environment exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo WARNING: Virtual environment not found. Using system Python.
    echo.
)

REM Check for API key
if "%GEMINI_API_KEY%"=="" (
    echo ERROR: GEMINI_API_KEY not set!
    echo.
    echo Please set your Gemini API key in .env or environment:
    echo   set GEMINI_API_KEY=your-api-key-here
    echo.
    pause
    exit /b 1
)

REM Change to tailor directory
cd /d "%~dp0tailor"

REM Run the tailor CLI
python tailor_cli.py %*

echo.
pause
