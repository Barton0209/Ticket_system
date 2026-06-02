# Инструкция по установке без root прав

## ✅ Приложение полностью бесплатное и работает без root прав

### Требования
- Python 3.9+ (уже установлен: 3.12.10)
- Node.js 18+ (для Electron UI, опционально)
- **НЕ требуется Docker**
- **НЕ требуются root права**
- **Все пакеты бесплатные (open source)**

---

## 🚀 Быстрый старт (без root прав)

### Шаг 1: Установка зависимостей Python (локально)

```bash
# Если нет прав на глобальную установку, используйте --user
pip install --user -r requirements.txt
pip install --user -r requirements-api.txt
pip install --user slowapi
```

**Альтернатива: виртуальное окружение (рекомендуется)**
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate  # Windows

pip install -r requirements.txt
pip install -r requirements-api.txt
pip install slowapi
```

### Шаг 2: Проверка структуры данных

```bash
# Папка data/ уже создана с правильными правами
ls -la data/
```

### Шаг 3: Настройка пользователей

Файл `users.local.json` уже создан с захешированными паролями:
- Admin: `secure_admin_password_123`
- ОП Пример: `пароль_подразделения`

**Для смены пароля:**
```bash
python -c "
from password_utils import hash_password
import json

with open('users.local.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Сменить пароль администратора
data['admin']['password'] = hash_password('ваш_новый_пароль')

with open('users.local.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print('Пароль обновлён')
"
```

### Шаг 4: Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```bash
cp .env.example .env
```

Отредактируйте `.env` и установите:
```bash
TICKET_API_KEY=your_secure_api_key_here
TICKET_ADMIN_PASSWORD=secure_admin_password_123
TICKET_API_HOST=127.0.0.1
TICKET_API_PORT=8765
TICKET_ENV=development
```

**Генерация безопасного API ключа:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Шаг 5: Tesseract OCR (опционально, без root)

#### Вариант A: Portable версия (Windows)
1. Скачайте portable версию: https://github.com/UB-Mannheim/tesseract/wiki
2. Распакуйте в любую папку (например, `C:\tesseract`)
3. В `.env` укажите:
   ```
   TESSERACT_CMD=C:\tesseract\tesseract.exe
   ```

#### Вариант B: Локальная установка (Linux/macOS без root)
```bash
# Скачать бинарник
wget https://github.com/tesseract-ocr/tesseract/releases/download/5.4.0/tesseract-5.4.0-linux-x86_64.tar.gz
tar xzf tesseract-5.4.0-linux-x86_64.tar.gz -C $HOME/.local

# Добавить в PATH
export PATH=$HOME/.local/bin:$PATH

# В .env указать:
TESSERACT_CMD=$HOME/.local/bin/tesseract
```

**Без Tesseract приложение работает**, но не может обрабатывать сканированные PDF (только текстовые).

---

## 🔧 Запуск приложения

### Вариант A: Tkinter Desktop UI

```bash
# Терминал 1: Запуск API сервера
python api_server.py

# Терминал 2: Запуск UI
python main.py
```

### Вариант B: Electron UI (требуется Node.js)

```bash
# Установка Node.js зависимостей (локально)
cd electron
npm install --no-save

# Запуск в режиме разработки
npm run dev
```

### Вариант C: Только API (для интеграции)

```bash
python api_server.py
# API доступно на http://127.0.0.1:8765
# Документация: http://127.0.0.1:8765/docs
```

---

## ✅ Проверка установки

```bash
python check_app.py
```

**Ожидаемый результат:**
```
[test_imports] OK (или WARN для Tkinter в headless)
[test_user_prefs] OK
[test_auth_config] OK
[test_routes] OK
...
Итого: 0-1 ошибок (не критично)
```

---

## 📁 Структура проекта

```
/workspace/
├── data/                    # Данные (создана, права 700)
│   ├── employees.db         # SQLite база
│   ├── employees_cache.pkl  # Кэш сотрудников
│   ├── users_cache.pkl      # Кэш пользователей
│   ├── user_prefs.json      # Настройки UI
│   └── app.log              # Логи
├── users.local.json         # Пользователи (bcrypt хеши)
├── .env                     # Переменные окружения (создайте из .env.example)
├── api_server.py            # API сервер
├── main.py                  # Tkinter UI
├── electron/                # Electron UI
└── *.md                     # Документация
```

---

## 🔐 Безопасность

### Что уже сделано:
- ✅ CORS ограничен localhost
- ✅ Rate limiting (5 запросов/мин на login)
- ✅ bcrypt для паролей
- ✅ Pickle файлы проверяются перед загрузкой
- ✅ Electron IPC защищён от path traversal

### Что нужно сделать вам:
1. Установить `TICKET_API_KEY` в `.env`
2. Сменить пароли по умолчанию
3. Ограничить доступ к папке `data/` (chmod 700)

---

## ❓ Частые вопросы

### Q: Нужно ли устанавливать пакеты глобально?
**A:** Нет! Используйте `--user` или виртуальное окружение.

### Q: Можно ли запустить без Tesseract?
**A:** Да! Приложение работает, но не обрабатывает сканированные PDF.

### Q: Требуется ли Docker?
**A:** Нет! Приложение работает нативно.

### Q: Нужны ли root права?
**A:** Нет! Все установки локальные (`--user` или venv).

### Q: Бесплатное ли приложение?
**A:** Да! Все зависимости open source (MIT/BSD/Apache лицензии).

---

## 📞 Поддержка

При проблемах:
1. Проверьте `data/app.log`
2. Запустите `python check_app.py`
3. Убедитесь, что все зависимости установлены
4. Проверьте переменные окружения в `.env`
