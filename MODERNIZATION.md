# Модернизация Ticket_system



Бесплатный стек, поэтапно. Текущая версия: **7.1** (Tkinter + API-заготовка).



## Этап 1 — текущее приложение ✅



| # | Задача | Статус |

|---|--------|--------|

| 1 | Разбить `main.py` → `ui/` | **Сделано** |

| 2 | SQLite (`data/employees.db`) | **Сделано** |

| 3 | PDF/OCR в фоне | **Сделано** |

| 4 | Пароли bcrypt, `users.local.json` | **Сделано** |

| 5 | Пагинация «База» | **Сделано** |

| 6 | Удалить мёртвый PySide6-код | **Сделано** |



---



## Этап 3 — современный UX (Tkinter) ✅ частично



| Функция | Файл / как включить |

|---------|---------------------|

| Toast-уведомления | `ui/toast.py` — автосохранение, база, черновик |

| Тёмная тема | **Вид → Тёмная тема** (полное применение после перезапуска) |

| Автосохранение черновика | каждые 5 мин (`data/user_prefs.json`) |

| Подсказки | при первом запуске; **Вид → Показать подсказки** |

| Горячие клавиши Excel | F2, Ctrl+Home/End в таблице заявки |



---



## Этап 2 — Electron + API 🚧



### Python API (готово)



```bat

run_api.bat

```



- `requirements-api.txt` — FastAPI + uvicorn

- `api_server.py` — REST поверх SQLite и PDF

- Порт по умолчанию: **8765** (`TICKET_API_HOST`, `TICKET_API_PORT`)

- Опционально: `TICKET_API_KEY` → заголовок `X-Api-Key`



### Electron (заготовка)



```bat

cd electron

npm install

npm run dev

```



См. `electron/README.md` — план React + AG Grid + pdf.js.



### Архитектура



```

Electron (React)  →  HTTP  →  api_server.py  →  employees_store / database

                         ↘  spawn  →  pdf_processor (OCR)

```



---



## Порядок полного переноса на Electron



1. ✅ SQLite + REST API

2. Логин + таблица заявки в React

3. Каталог и поиск

4. PDF (pdf.js + `POST /pdf/process`)

5. Экспорт Excel (exceljs или Python)
