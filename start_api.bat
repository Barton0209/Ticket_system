@echo off
REM Запуск API сервера (Windows, без root прав)
call venv\Scripts\activate.bat 2>nul || echo [INFO] Виртуальное окружение не найдено, используем системный Python
echo [INFO] Запуск API сервера...
python api_server.py
pause
