@echo off

:: Check if Python is available
for /f "delims=" %%P in ('python --version 2^>nul') do set "PYTHON_VERSION=%%P"
if not defined PYTHON_VERSION (
    echo Python is not installed or not found in PATH. Please install Python.
    pause
    exit /b
)
echo Found %PYTHON_VERSION%

:: Check if virtual environment exists, create if not
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate the virtual environment
echo Activating virtual environment...
call venv\Scripts\activate

:: Install dependencies if not already installed
if not exist venv\Lib\site-packages\installed (
    if exist requirements.txt (
        echo Installing wheel for faster installation...
        python -m pip install --upgrade pip --no-cache-dir
        python -m pip install wheel
        echo Installing dependencies...
        python -m pip install -r requirements.txt || (
            echo Failed to install dependencies. Please check requirements.txt for issues.
            pause
            exit /b
        )
        echo. > venv\Lib\site-packages\installed
    ) else (
        echo requirements.txt not found, skipping dependency installation.
    )
) else (
    echo Dependencies already installed, skipping installation.
)

:: Start and restart the bot in a loop
:loop
echo Starting the bot...
venv\Scripts\python.exe main.py || (
    echo Failed to start the bot. Retrying in 2 seconds...
)
echo Restarting the program in 2 seconds...
timeout /t 2 /nobreak >nul
goto :loop
