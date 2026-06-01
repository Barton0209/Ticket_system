@echo off

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (

    echo Создайте venv и установите зависимости.

    pause

    exit /b 1

)

venv\Scripts\pip.exe install -q -r requirements-api.txt

echo API: http://127.0.0.1:8765  (ключ: TICKET_API_KEY, если задан)

venv\Scripts\python.exe api_server.py

if errorlevel 1 pause
