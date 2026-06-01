# app_logger.py
"""Логирование приложения в data/app.log."""

import logging
from logging.handlers import RotatingFileHandler

from config import DATA_DIR

LOG_FILE = DATA_DIR / "app.log"


def setup_logging() -> logging.Logger:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ticket_system")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    logger.addHandler(handler)
    return logger


log = setup_logging()
