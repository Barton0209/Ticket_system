# Полное руководство по установке и настройке Ticket System v7.2

## 📋 Требования

### Обязательные
- Python 3.9+ (протестировано на 3.12)
- Node.js 18+ (для Electron UI)
- Операционная система: Windows 10+, Linux, macOS

### Рекомендуемые
- Tesseract OCR 5.x (для обработки сканированных PDF)
- Минимум 4 GB RAM
- 1 GB свободного места на диске

---

## 🚀 Быстрый старт

### Шаг 1: Установка зависимостей Python

```bash
pip install -r requirements.txt
pip install -r requirements-api.txt
pip install slowapi  # rate limiting для API
```

### Шаг 2: Создание структуры данных

```bash
mkdir data
chmod 700 data  # Linux/macOS
```

### Шаг 3: Настройка пользователей

```bash
# Создать users.local.json с захешированными паролями
python -c "
from password_utils import hash_password
import json

data = {
    'users': {'ОП Пример': hash_password('пароль_подразделения')},
    'admin': {'username': 'Admin', 'password': hash_password('secure_admin_password_123')}
}

with open('users.local.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print('users.local.json создан')
"
```

### Шаг 4: Настройка переменных окружения

Создайте файл `.env` (или установите переменные вручную):

```bash
cp .env.example .env
# Отредактируйте .env и установите свои значения
```

**Минимальные требуемые переменные:**
```bash
TICKET_API_KEY=your_secure_api_key_here
TICKET_ADMIN_PASSWORD=secure_admin_password_123
```

### Шаг 5: Установка Tesseract OCR (опционально, но рекомендуется)

#### Windows
1. Скачайте установщик: https://github.com/UB-Mannheim/tesseract/wiki
2. Установите в `C:\Program Files\Tesseract-OCR`
3. Добавьте в PATH или установите переменную:
   ```bash
   set TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
   ```

#### Linux (Debian/Ubuntu)
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng
```

#### macOS
```bash
brew install tesseract
brew install tesseract-lang
```

---

## 🔧 Запуск приложения

### Вариант A: Tkinter Desktop UI

```bash
# Запуск API сервера (в отдельном терминале)
python api_server.py

# Запуск desktop приложения
python main.py
```

Или используйте batch-файлы (Windows):
```bash
run_api.bat
run.bat
```

### Вариант B: Electron UI

```bash
cd electron

# Установка зависимостей Node.js
npm install

# Запуск в режиме разработки
npm run dev
```

Или используйте batch-файл (Windows):
```bash
run_electron_dev.bat
```

---

## ✅ Проверка установки

Запустите скрипт проверки:

```bash
python check_app.py
```

**Ожидаемый результат:**
```
✓ Все зависимости установлены
✓ Папка data/ существует
✓ users.local.json найден
✓ Конфигурация загружена
```

---

## 📁 Структура проекта

```
/workspace/
├── data/                    # Хранилище данных (SQLite, кэш, логи)
│   ├── employees.db         # База сотрудников (SQLite)
│   ├── employees_cache.pkl  # Кэш сотрудников
│   ├── users_cache.pkl      # Кэш пользователей
│   └── app.log              # Логи приложения
├── electron/                # Electron UI приложение
│   ├── src/                 # React компоненты
│   ├── main.js              # Electron главный процесс
│   └── preload.js           # Preload скрипт
├── ui/                      # Tkinter UI компоненты
├── api_server.py            # FastAPI сервер
├── config.py                # Конфигурация
├── database.py              # Работа с БД
├── users_manager.py         # Управление пользователями
├── password_utils.py        # Хеширование паролей
├── pdf_processor.py         # Обработка PDF
└── requirements*.txt        # Зависимости Python
```

---

## 🔐 Настройка безопасности

См. подробное руководство в [SECURITY.md](SECURITY.md).

**Краткий чек-лист:**
- [ ] Установлен `TICKET_API_KEY`
- [ ] Установлен `TICKET_ADMIN_PASSWORD`
- [ ] Пароли захешированы через bcrypt
- [ ] Папка `data/` защищена (chmod 700)
- [ ] CORS настроен на конкретные домены

---

## 🛠️ Решение проблем

### Ошибка: "Employee database not loaded"
**Решение:** Загрузите базу сотрудников через UI (Настройки → Загрузить базу) или поместите файл Excel в папку data/.

### Ошибка: "Tesseract not found"
**Решение:** Установите Tesseract OCR и задайте переменную `TESSERACT_CMD`.

### Ошибка: "Invalid API key"
**Решение:** Убедитесь, что `TICKET_API_KEY` установлен одинаково в API сервере и клиенте.

### Ошибка: "Pickle file corrupted"
**Решение:** Удалите повреждённый `.pkl` файл и перезагрузите данные из источника.

---

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи в `data/app.log`
2. Запустите `python check_app.py` для диагностики
3. Убедитесь, что все зависимости установлены

---

## 📝 Обновление

При обновлении версии:
1. Сделайте резервную копию папки `data/`
2. Обновите код: `git pull`
3. Обновите зависимости: `pip install -r requirements.txt --upgrade`
4. Проверьте миграции базы данных (если есть)
