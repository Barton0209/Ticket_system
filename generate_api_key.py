#!/usr/bin/env python3
"""Генерация уникального API ключа для .env файла"""
import secrets

api_key = secrets.token_hex(32)
print(f"\n{'='*60}")
print("Уникальный API ключ для TICKET_API_KEY:")
print(f"{'='*60}")
print(f"TICKET_API_KEY={api_key}")
print(f"{'='*60}\n")
print("Скопируйте эту строку в файл .env")
