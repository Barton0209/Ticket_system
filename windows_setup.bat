@echo off
REM ============================================
REM Ticket System - Windows Setup Script
REM Для запуска без root прав
REM ============================================

echo [Ticket System] Настройка для Windows
echo ==========================================

REM 1. Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не найден. Установите Python 3.9+ с python.org
    pause
    exit /b 1
)
echo [OK] Python найден

REM 2. Создание виртуального окружения (рекомендуется)
if not exist "venv" (
    echo [INFO] Создание виртуального окружения...
    python -m venv venv
) else (
    echo [OK] Виртуальное окружение уже существует
)

REM 3. Активация виртуального окружения
echo [INFO] Активация виртуального окружения...
call venv\Scripts\activate.bat

REM 4. Установка зависимостей
echo [INFO] Установка Python зависимостей...
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-api.txt

REM 5. Проверка Node.js для Electron UI (опционально)
node --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Node.js не найден. Electron UI будет недоступен.
    echo          Используйте Tkinter UI или установите Node.js с nodejs.org
) else (
    echo [OK] Node.js найден
    echo [INFO] Установка Electron зависимостей...
    cd electron
    call npm install
    cd ..
)

REM 6. Создание папки data
if not exist "data" (
    echo [INFO] Создание папки data...
    mkdir data
)
echo [OK] Папка data готова

REM 7. Создание users.local.json из примера
if not exist "users.local.json" (
    echo [INFO] Копирование users.local.json.example -> users.local.json
    copy users.local.json.example users.local.json
    echo [WARNING] Не забудьте захешировать пароли и сменить их!
) else (
    echo [OK] users.local.json уже существует
)

REM 8. Создание .env файла
if not exist ".env" (
    echo [INFO] Копирование .env.example -> .env
    copy .env.example .env
    echo [WARNING] Отредактируйте .env и задайте уникальные пароли/API ключи!
) else (
    echo [OK] .env уже существует
)

echo.
echo ==========================================
echo [SUCCESS] Настройка завершена!
echo.
echo Следующие шаги:
echo 1. Отредактируйте .env и задайте:
echo    - TICKET_API_KEY=уникальный_ключ
echo    - TICKET_ADMIN_PASSWORD=ваш_пароль
echo 2. Захешируйте пароли в users.local.json через password_utils.py
echo 3. Запустите API: python api_server.py
echo 4. Запустите UI: python main.py
echo.
echo Или используйте:
echo   - start_api.bat для запуска API
echo   - start_ui.bat для запуска Tkinter UI
echo   - npm run dev (в папке electron) для Electron UI
echo ==========================================
pause
