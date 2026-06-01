# Electron UI (этап 2)

React + AG Grid клиент поверх Python API.

## Запуск (разработка)

1. **Терминал 1** — из корня проекта:

   ```bat
   run_api.bat
   ```

2. **Терминал 2**:

   ```bat
   run_electron_dev.bat
   ```

   Или вручную:

   ```bat
   cd electron
   npm install
   npm run dev
   ```

Откроется окно Electron с вкладками **Поиск в базе**, **Из списка**, **Заявка**.

## Сборка без dev-сервера

```bat
cd electron
npm run build
npm run electron
```

## API

| Метод | Путь |
|-------|------|
| GET | `/health` |
| GET | `/departments` |
| POST | `/employees/search` |
| POST | `/employees/lookup/batch` |
| GET | `/employees/lookup/fio` |
| POST | `/pdf/process` |
| GET | `/routes` |

После изменения `api_server.py` перезапустите `run_api.bat`.

## Из списка (как в Tkinter)

- Вставьте ФИО → **Поиск**
- Жёлтые строки «Несколько» — **двойной клик** → выбор сотрудника
- **Составить заявку** — добавляет найденных на вкладку «Заявка»

## Дальше

- Экспорт Excel (exceljs или Python)
- pdf.js + `POST /pdf/process`
- Логин через API users
