import sqlite3
from typing import Optional

from Common.db import get_connection
from Common.settings import DB_PATH


class OrdersRepository:

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()


    # ------------------------------
    # Подключение к БД
    # ------------------------------
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            cur = conn.cursor()

            cur.execute("PRAGMA foreign_keys = ON;")
            cur.execute("PRAGMA journal_mode = WAL;")
            cur.execute("PRAGMA synchronous = NORMAL;")

            # ------------------------------
            # Таблица заказов
            # ------------------------------
            cur.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    posting_number TEXT UNIQUE NOT NULL,
                    status TEXT NOT NULL,

                    -- флаг наличия зависимостей
                    has_requirements INTEGER DEFAULT 0,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ------------------------------
            # Таблица позиций в заказе
            # ------------------------------
            cur.execute("""
                CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    order_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    offer_id TEXT NOT NULL,
                    quantity INTEGER NOT NULL CHECK(quantity > 0),

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (order_id)
                        REFERENCES orders(id)
                        ON DELETE CASCADE
                )
            """)


            # ------------------------------
            # Таблица зависимостей заказов
            # ------------------------------
            cur.execute("""
                CREATE TABLE IF NOT EXISTS order_requirements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,

                    -- тип зависимости (marks, documents, extras, ...)
                    requirement_type TEXT NOT NULL,

                    -- значение зависимости (fragile, box, invoice, ...)
                    requirement_value TEXT NOT NULL,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (order_id)
                        REFERENCES orders(id)
                        ON DELETE CASCADE
                )
            """)

            # ------------------------------
            # Индексы
            # ------------------------------
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_orders_posting_number
                ON orders(posting_number)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_order_requirements_order_id
                ON order_requirements(order_id)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_order_requirements_type_value
                ON order_requirements(requirement_type, requirement_value)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_order_items_order_id
                ON order_items(order_id)
            """)

            conn.commit()


    # ---------- CREATE ----------

    def create_order(
        self,
        posting_number: str,
        status: str,
        has_requirements: bool = False,
    ) -> None:
        """
        Создаёт заказ.
        Повторный вызов безопасен (INSERT OR IGNORE).
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO orders (
                    posting_number,
                    status,
                    has_requirements
                )
                VALUES (?, ?, ?)
            """, (
                posting_number,
                status,
                int(has_requirements),
            ))
            conn.commit()

    def create_order_with_items(
            self,
            posting_number: str,
            status: str,
            has_requirements: bool,
            items: list[dict]
    ) -> int:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA foreign_keys = ON;")

            # 1. создаём заказ
            cur.execute("""
                INSERT INTO orders (posting_number, status, has_requirements)
                VALUES (?, ?, ?)
            """, (posting_number, status, int(has_requirements)))

            order_id = cur.lastrowid

            # 2. создаём позиции
            order_items = [
                (
                    order_id,
                    item["product_id"],
                    item["offer_id"],
                    item["quantity"]
                )
                for item in items
            ]

            cur.executemany("""
                INSERT INTO order_items
                (order_id, product_id, offer_id, quantity)
                VALUES (?, ?, ?, ?)
            """, order_items)

            conn.commit()
            return order_id

    def create_requirements(self, order_id: int, requirement_type: str, requirement_value: str) -> None:
        """
        Создает запись в таблице зависимостей
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO order_requirements (
                    order_id,
                    requirement_type,
                    requirement_value
                )
                VALUES (?, ?, ?)
                """,
                (order_id, requirement_type, requirement_value)
            )
            conn.commit()

    # ---------- READ ----------

    def get_status(self, posting_number: str) -> Optional[str]:
        """
        Возвращает статус заказа по posting_number.
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status
                FROM orders
                WHERE posting_number = ?
            """, (posting_number,))
            row = cursor.fetchone()
            return row["status"] if row else None

    def get_by_posting_number(self, posting_number: str) -> Optional[dict]:
        """
        Возвращает заказ целиком.
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT *
                FROM orders
                WHERE posting_number = ?
            """, (posting_number,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_id_by_posting_number(self, posting_number: str) -> Optional[int]:
        """
        Возвращает id заказа.
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id
                FROM orders
                WHERE posting_number = ?
            """, (posting_number,))
            row = cursor.fetchone()
            return row["id"] if row else None

    def get_all_orders(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT *
                FROM orders
            """,)
            return [self._row_to_dict(r) for r in cursor.fetchall()]

    def get_all_requirements(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT *
                FROM order_requirements
            """,)
            return [self._row_to_dict(r) for r in cursor.fetchall()]

    def get_all_items(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT *
                FROM order_items
            """,)
            return [self._row_to_dict(r) for r in cursor.fetchall()]

    # ---------- UPDATE ----------

    def update_status(self, posting_number: str, new_status: str) -> None:
        """
        Обновляет статус заказа.
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE orders
                SET
                    status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE posting_number = ?
            """, (new_status, posting_number))
            conn.commit()

    def set_has_requirements(self, posting_number: str, value: bool) -> None:
        """
        Обновляет флаг наличия зависимостей.
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE orders
                SET
                    has_requirements = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE posting_number = ?
            """, (int(value), posting_number))
            conn.commit()

    # ---------- DELETE (опционально) ----------

    def delete(self, posting_number: str) -> None:
        """
        Удаляет заказ.
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM orders
                WHERE posting_number = ?
            """, (posting_number,))
            conn.commit()


    # ------------------------------
    # Helpers
    # ------------------------------
    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        return {k: row[k] for k in row.keys()}