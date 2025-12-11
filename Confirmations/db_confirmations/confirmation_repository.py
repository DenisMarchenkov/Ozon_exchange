import sqlite3
from datetime import datetime
from Common.settings import DB_PATH


class ConfirmationsRepository:
    """
    Репозиторий для работы с таблицами confirmations и confirmation_items.
    ORM-заменитель на sqlite.
    """

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_tables()

    # ------------------------------------------
    # Внутренние методы
    # ------------------------------------------

    def _get_conn(self):
        """Создаёт новое подключение к БД."""
        return sqlite3.connect(self.db_path)

    def _init_tables(self):
        """Создаёт таблицы, если их ещё нет."""
        with self._get_conn() as conn:
            cur = conn.cursor()

            cur.execute("""
                CREATE TABLE IF NOT EXISTS confirmations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    posting_number TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS confirmation_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    confirmation_id INTEGER NOT NULL,
                    sku TEXT NOT NULL,
                    name TEXT,
                    quantity INTEGER NOT NULL,
                    item_status TEXT DEFAULT 'OK',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (confirmation_id)
                        REFERENCES confirmations(id)
                        ON DELETE CASCADE
                )
            """)

            conn.commit()

    # ------------------------------------------
    # Confirmations CRUD
    # ------------------------------------------

    def add_confirmation(self, posting_number: str, status: str = "NEW") -> int:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO confirmations (posting_number, status)
                VALUES (?, ?)
            """, (posting_number, status))
            conn.commit()
            return cur.lastrowid

    def update_status(self, posting_number: str, new_status: str):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE confirmations
                SET status=?, updated_at=?
                WHERE posting_number=?
            """, (new_status, datetime.utcnow(), posting_number))
            conn.commit()

    def get_by_posting(self, posting_number: str):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, posting_number, status, created_at, updated_at
                FROM confirmations
                WHERE posting_number=?
            """, (posting_number,))
            return cur.fetchone()

    def get_all(self):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, posting_number, status, created_at, updated_at
                FROM confirmations
                ORDER BY id DESC
            """)
            return cur.fetchall()

    def delete_confirmation(self, posting_number: str):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM confirmations WHERE posting_number=?", (posting_number,))
            conn.commit()

    # ------------------------------------------
    # Items CRUD
    # ------------------------------------------

    def add_item(self, confirmation_id: int, sku: str, name: str, quantity: int, item_status="OK"):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO confirmation_items (confirmation_id, sku, name, quantity, item_status)
                VALUES (?, ?, ?, ?, ?)
            """, (confirmation_id, sku, name, quantity, item_status))
            conn.commit()
            return cur.lastrowid

    def get_items(self, confirmation_id: int):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, sku, name, quantity, item_status, created_at, updated_at
                FROM confirmation_items
                WHERE confirmation_id=?
            """, (confirmation_id,))
            return cur.fetchall()
