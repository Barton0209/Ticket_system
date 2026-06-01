@echo off

cd /d "%~dp0"

echo 1) Запустите run_api.bat в другом окне

echo 2) Сейчас стартует Electron + React...

cd electron

if not exist node_modules (

  echo npm install...

  call npm install

)

call npm run dev

pause
