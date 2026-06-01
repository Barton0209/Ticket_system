@echo off
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
    echo Создайте venv: python -m venv venv
    echo Затем: venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)
venv\Scripts\python.exe main.py
if errorlevel 1 (
    echo.
    echo Ошибка запуска. Сообщение выше.
    pause
)
