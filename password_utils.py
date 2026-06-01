# password_utils.py
"""Хеширование паролей (bcrypt)."""

from __future__ import annotations

import bcrypt

_PREFIX = "$2b$"


def hash_password(plain: str) -> str:
    if not plain:
        return ""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, stored: str) -> bool:
    if not plain or not stored:
        return False
    if not is_hashed(stored):
        return plain == stored
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), stored.encode("utf-8"))
    except ValueError:
        return False


def is_hashed(value: str) -> bool:
    return isinstance(value, str) and value.startswith(_PREFIX)
