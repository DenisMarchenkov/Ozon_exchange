import os
import logging

from logging.handlers import TimedRotatingFileHandler
from Common.settings import BASE_DIR, DEV_MODE

LOG_DIR = os.path.join(BASE_DIR, "Logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "exchange.log")


def get_logger(name: str) -> logging.Logger:
    """
    Возвращает настроенный логгер для любого модуля или приложения.
    """
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger  # Уже настроен

    logger.setLevel(logging.DEBUG if DEV_MODE else logging.INFO)

    # Файл с ротацией
    file_handler = TimedRotatingFileHandler(
        LOG_FILE, when="midnight", interval=1, backupCount=14, encoding="utf-8"
    )
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Вывод в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger