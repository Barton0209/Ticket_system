@echo off
REM Запуск Tkinter UI (Windows, без root прав)
call venv\Scripts\activate.bat 2>nul || echo [INFO] Виртуальное окружение не найдено, используем системный Python
echo [INFO] Запуск интерфейса...
python main.py
pause
