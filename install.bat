@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Установка Ticket_system ===

where python >nul 2>&1
if errorlevel 1 (
    echo Установите Python 3.9+ с https://www.python.org/
    pause
    exit /b 1
)

if not exist "venv\Scripts\python.exe" (
    echo Создание venv...
    python -m venv venv
)

echo Установка зависимостей...
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\pip.exe install -r requirements.txt

echo.
echo Проверка модулей...
venv\Scripts\python.exe check_app.py
if errorlevel 1 (
    echo Проверка завершилась с ошибками.
    pause
    exit /b 1
)

echo.
echo Готово. Запуск: run.bat
pause
