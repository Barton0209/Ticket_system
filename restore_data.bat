@echo off
REM Восстановление данных из резервной копии (Windows, без root прав)
echo Доступные резервные копии:
dir /B /OD backup_*
echo.
set /p BACKUP_DIR="Введите имя папки для восстановления: "

if not exist "%BACKUP_DIR%" (
    echo [ERROR] Папка не найдена!
    pause
    exit /b 1
)

echo [WARNING] Текущие данные будут заменены!
set /p CONFIRM="Продолжить? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo Отменено.
    pause
    exit /b 0
)

echo [INFO] Восстановление из %BACKUP_DIR%...
if exist "%BACKUP_DIR%\data" xcopy /E /I /Y "%BACKUP_DIR%\data" data
if exist "%BACKUP_DIR%\users.local.json" xcopy /Y "%BACKUP_DIR%\users.local.json" .
if exist "%BACKUP_DIR%\.env" xcopy /Y "%BACKUP_DIR%\.env" .

echo [OK] Восстановление завершено!
pause
