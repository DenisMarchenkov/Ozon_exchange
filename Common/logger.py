import os
import logging
from logging.handlers import TimedRotatingFileHandler
from Common.settings import BASE_DIR, DEV_MODE

LOG_DIR = os.path.join(BASE_DIR, "Logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "exchange.log")


def get_logger(name: str) -> logging.Logger:
    """
    Глобальный логгер, корректно работающий на Windows.
    Все модули получают один и тот же handler.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if DEV_MODE else logging.INFO)

    # --- хак: handlers проверяются только для ROOT-логгера ---
    root_logger = logging.getLogger()

    if not root_logger.handlers:
        # Создаём handlers только ОДИН раз!
        root_logger.setLevel(logging.DEBUG if DEV_MODE else logging.INFO)
        # Файл с ротацией
        file_handler = TimedRotatingFileHandler(
            LOG_FILE,
            when="midnight",
            interval=1,
            backupCount=14,
            encoding="utf-8",
            delay=True,          # <-- критично важно для Windows
            utc=False
        )
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        ))
        root_logger.addHandler(file_handler)

        # Консоль — только DEV
        if DEV_MODE:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
            ))
            root_logger.addHandler(console_handler)

    # Чтобы логгеры не дублировали сообщения
    logger.propagate = True

    return logger
