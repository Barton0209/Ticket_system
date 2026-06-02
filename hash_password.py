#!/usr/bin/env python3
"""Хеширование пароля через bcrypt для users.local.json"""
import sys
import getpass

try:
    import bcrypt
except ImportError:
    print("[ERROR] bcrypt не установлен. Выполните: pip install bcrypt")
    sys.exit(1)

if len(sys.argv) > 1:
    password = sys.argv[1]
else:
    password = getpass.getpass("Введите пароль для хеширования: ")

hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))
print(f"\n{'='*60}")
print("bcrypt хеш пароля:")
print(f"{'='*60}")
print(hashed.decode('utf-8'))
print(f"{'='*60}\n")
print("Используйте этот хеш в users.local.json вместо открытого пароля")
