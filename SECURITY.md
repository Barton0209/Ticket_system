# Руководство по безопасности Ticket System

## 🔐 Критические настройки безопасности

### 1. API Key (ОБЯЗАТЕЛЬНО для production)

```bash
export TICKET_API_KEY="your_secure_random_key_here"
```

**Генерация безопасного ключа:**
```bash
# Linux/macOS
openssl rand -hex 32

# Python
python -c "import secrets; print(secrets.token_hex(32))"
```

⚠️ **Без TICKET_API_KEY API доступен всем!**

---

### 2. Пароль администратора

```bash
export TICKET_ADMIN_PASSWORD="secure_password_here"
```

**Требования к паролю:**
- Минимум 12 символов
- Заглавные и строчные буквы
- Цифры и специальные символы
- Не использовать словарные слова

---

### 3. Файл users.local.json

Храните только хешированные пароли:

```json
{
  "users": {
    "ОП Пример": "$2b$12$..."
  },
  "admin": {
    "username": "Admin",
    "password": "$2b$12$..."
  }
}
```

**Создание хеша пароля:**
```bash
python -c "from password_utils import hash_password; print(hash_password('your_password'))"
```

---

### 4. Защита папки data/

```bash
# Linux/macOS
chmod 700 data/
chown your_user:your_group data/

# Windows (PowerShell)
icacls data /grant your_user:(OI)(CI)F /inheritance:r
```

---

### 5. CORS настройки

В `api_server.py` измените `ALLOWED_ORIGINS` для production:

```python
ALLOWED_ORIGINS = [
    "https://your-domain.com",
    "app://your-electron-app",
]
```

---

## 🛡️ Дополнительные меры

### Rate Limiting
Включён по умолчанию для `/auth/login` (5 запросов/минуту).

###_pickle файлы
Все pickle файлы проверяются на:
- Нулевой размер
- Превышение лимита размера
- Целостность перед загрузкой

### Electron Security
- Context Isolation: ✅ включён
- Node Integration: ✅ отключён
- Path validation: ✅ реализована

---

## 📋 Чек-лист перед запуском в production

- [ ] Установлен `TICKET_API_KEY`
- [ ] Установлен `TICKET_ADMIN_PASSWORD`
- [ ] Пароли в `users.local.json` захешированы через bcrypt
- [ ] Папка `data/` имеет ограничения доступа (chmod 700)
- [ ] CORS настроен на конкретные домены
- [ ] Tesseract OCR установлен (для обработки сканов)
- [ ] Файл `.env` создан с правильными правами (chmod 600)
- [ ] Резервное копирование настроено

---

## 🚨 Что НЕЛЬЗЯ делать

❌ Хранить пароли в открытом виде в репозитории  
❌ Использовать `allow_origins=["*"]` в production  
❌ Запускать API без `TICKET_API_KEY`  
❌ Давать доступ к папке `data/` другим пользователям  
❌ Логировать пароли или API ключи  

---

## 📞 Экстренные действия

### Если API ключ скомпрометирован:
1. Немедленно смените `TICKET_API_KEY`
2. Перезапустите API сервер
3. Обновите ключ во всех клиентах

### Если пароль администратора скомпрометирован:
1. Смените `TICKET_ADMIN_PASSWORD`
2. Перезапустите приложение
3. Проверьте логи на подозрительную активность

### Если данные утекли:
1. Изолируйте систему от сети
2. Сохраните логи для расследования
3. Уведомите заинтересованные стороны
