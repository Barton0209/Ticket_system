@echo off
REM Резервное копирование данных (Windows, без root прав)
set BACKUP_DIR=backup_%DATE:~-4,4%%DATE:~-7,2%%DATE:~-10,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%
set BACKUP_DIR=%BACKUP_DIR: =0%
echo [INFO] Создание резервной копии в %BACKUP_DIR%...

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

xcopy /E /I /Y data "%BACKUP_DIR%\data"
xcopy /E /I /Y users.local.json "%BACKUP_DIR%\" 2>nul
xcopy /E /I /Y .env "%BACKUP_DIR%\" 2>nul

echo [OK] Резервная копия создана: %BACKUP_DIR%
pause
