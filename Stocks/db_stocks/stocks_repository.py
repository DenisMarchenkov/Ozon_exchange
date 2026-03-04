import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from Common.settings import DB_PATH
from Common.db.database import Database
from Common.logger import get_logger

logger = get_logger(__name__)


class StocksRepository:
    """
    Репозиторий для работы с логами обновления остатков и таймера минимальной цены.
    """

    def __init__(self, db: Optional[Database] = None):
        if db is None:
            db = Database(DB_PATH)
        self.db = db
        self._init_db()

    def _init_db(self):
        """Создает таблицы, если они не существуют."""
        with self.db.connect() as conn:
            cur = conn.cursor()
            
            # Таблица логов сеансов обновления остатков
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stock_update_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_timestamp TEXT NOT NULL,
                    total_offers_in_file INTEGER,
                    total_offers_in_ozon INTEGER,
                    items_updated INTEGER,
                    status TEXT NOT NULL
                )
            """)
            
            # Таблица логирования каждого обновленного товара (история)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stock_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    update_log_id INTEGER,
                    date TEXT NOT NULL,
                    offer_id TEXT NOT NULL,
                    product_id INTEGER NOT NULL,
                    stock_value INTEGER NOT NULL,
                    FOREIGN KEY (update_log_id) REFERENCES stock_update_logs(id)
                )
            """)

            # Таблица логов сеансов обновления таймера промо-акций
            cur.execute("""
                CREATE TABLE IF NOT EXISTS promo_timer_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_timestamp TEXT NOT NULL,
                    total_items INTEGER,
                    status TEXT NOT NULL
                )
            """)

            # Таблица истории обновления таймера промо-акций для каждого товара
            cur.execute("""
                CREATE TABLE IF NOT EXISTS promo_timer_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timer_log_id INTEGER,
                    product_id INTEGER NOT NULL,
                    FOREIGN KEY (timer_log_id) REFERENCES promo_timer_logs(id)
                )
            """)

            conn.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).date().isoformat()

    # ---------------------------------------------------------
    # Логирование обновления остатков
    # ---------------------------------------------------------
    def create_stock_update_session(self, total_file: int, total_ozon: int, status: str = "STARTED") -> int:
        """Создает запись о начале сеанса обновления остатков."""
        try:
            with self.db.connect() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO stock_update_logs
                    (run_timestamp, total_offers_in_file, total_offers_in_ozon, items_updated, status)
                    VALUES (?, ?, ?, ?, ?)
                """, (self._now(), total_file, total_ozon, 0, status))
                conn.commit()
                return cur.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при создании сессии обновления остатков: {e}")
            return -1

    def finish_stock_update_session(self, log_id: int, items_updated: int, status: str = "SUCCESS"):
        """Завершает сеанс обновления остатков, записывая результат."""
        if log_id <= 0: return

        try:
            with self.db.connect() as conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE stock_update_logs
                    SET items_updated = ?, status = ?
                    WHERE id = ?
                """, (items_updated, status, log_id))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при завершении сессии обновления остатков (ID {log_id}): {e}")

    def save_stock_history_bulk(self, log_id: int, stocks_to_update: List[Dict[str, Any]]):
        """Массово сохраняет историю отправленных остатков."""
        if log_id <= 0 or not stocks_to_update:
            return

        today = self._today()
        records = [
            (log_id, today, item["offer_id"], item["product_id"], item["stock"])
            for item in stocks_to_update
        ]

        try:
            with self.db.connect() as conn:
                cur = conn.cursor()
                cur.executemany("""
                    INSERT INTO stock_history
                    (update_log_id, date, offer_id, product_id, stock_value)
                    VALUES (?, ?, ?, ?, ?)
                """, records)
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при сохранении истории остатков (Log ID {log_id}): {e}")

    # ---------------------------------------------------------
    # Логирование таймера промо-акций (Promo)
    # ---------------------------------------------------------
    def create_promo_timer_session(self, total_items: int, status: str = "STARTED") -> int:
        """Создает запись о начале сеанса обновления таймера промо-акций."""
        try:
            with self.db.connect() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO promo_timer_logs
                    (run_timestamp, total_items, status)
                    VALUES (?, ?, ?)
                """, (self._now(), total_items, status))
                conn.commit()
                return cur.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при создании сессии обновления таймера промо: {e}")
            return -1

    def finish_promo_timer_session(self, log_id: int, status: str = "SUCCESS"):
        """Завершает сеанс обновления таймера промо-акций."""
        if log_id <= 0: return

        try:
            with self.db.connect() as conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE promo_timer_logs
                    SET status = ?
                    WHERE id = ?
                """, (status, log_id))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при завершении сессии обновления таймера промо (ID {log_id}): {e}")

    def save_promo_timer_history_bulk(self, log_id: int, product_ids: List[int]):
        """Массово сохраняет историю обновления таймера промо-акций для товаров."""
        if log_id <= 0 or not product_ids:
            return

        records = [(log_id, pid) for pid in product_ids]

        try:
            with self.db.connect() as conn:
                cur = conn.cursor()
                cur.executemany("""
                    INSERT INTO promo_timer_history
                    (timer_log_id, product_id)
                    VALUES (?, ?)
                """, records)
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при сохранении истории таймеров промо (Log ID {log_id}): {e}")
