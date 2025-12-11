# import sqlite3
# from datetime import datetime
# from Common.settings import DB_PATH
#
#
# class ConfirmationsRepository:
#     """
#     Репозиторий для работы с таблицами confirmations и confirmation_items.
#     ORM-заменитель на sqlite.
#     """
#
#     def __init__(self, db_path=DB_PATH):
#         self.db_path = db_path
#         self._init_tables()
#
#     # ------------------------------------------
#     # Внутренние методы
#     # ------------------------------------------
#
#     def _get_conn(self):
#         """Создаёт новое подключение к БД."""
#         return sqlite3.connect(self.db_path)
#
#     def _init_tables(self):
#         """Создаёт таблицы, если их ещё нет."""
#         with self._get_conn() as conn:
#             cur = conn.cursor()
#
#             cur.execute("""
#                 CREATE TABLE IF NOT EXISTS confirmations (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     posting_number TEXT NOT NULL UNIQUE,
#                     status TEXT NOT NULL,
#                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#                 )
#             """)
#
#             cur.execute("""
#                 CREATE TABLE IF NOT EXISTS confirmation_items (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     confirmation_id INTEGER NOT NULL,
#                     sku TEXT NOT NULL,
#                     name TEXT,
#                     quantity INTEGER NOT NULL,
#                     item_status TEXT DEFAULT 'OK',
#                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#
#                     FOREIGN KEY (confirmation_id)
#                         REFERENCES confirmations(id)
#                         ON DELETE CASCADE
#                 )
#             """)
#
#             conn.commit()
#
#     # ------------------------------------------
#     # Confirmations CRUD
#     # ------------------------------------------
#
#     def add_confirmation(self, posting_number: str, status: str = "NEW") -> int:
#         with self._get_conn() as conn:
#             cur = conn.cursor()
#             cur.execute("""
#                 INSERT INTO confirmations (posting_number, status)
#                 VALUES (?, ?)
#             """, (posting_number, status))
#             conn.commit()
#             return cur.lastrowid
#
#     def update_status(self, posting_number: str, new_status: str):
#         with self._get_conn() as conn:
#             cur = conn.cursor()
#             cur.execute("""
#                 UPDATE confirmations
#                 SET status=?, updated_at=?
#                 WHERE posting_number=?
#             """, (new_status, datetime.utcnow(), posting_number))
#             conn.commit()
#
#     def get_by_posting(self, posting_number: str):
#         with self._get_conn() as conn:
#             cur = conn.cursor()
#             cur.execute("""
#                 SELECT id, posting_number, status, created_at, updated_at
#                 FROM confirmations
#                 WHERE posting_number=?
#             """, (posting_number,))
#             return cur.fetchone()
#
#     def get_all(self):
#         with self._get_conn() as conn:
#             cur = conn.cursor()
#             cur.execute("""
#                 SELECT id, posting_number, status, created_at, updated_at
#                 FROM confirmations
#                 ORDER BY id DESC
#             """)
#             return cur.fetchall()
#
#     def delete_confirmation(self, posting_number: str):
#         with self._get_conn() as conn:
#             cur = conn.cursor()
#             cur.execute("DELETE FROM confirmations WHERE posting_number=?", (posting_number,))
#             conn.commit()
#
#     # ------------------------------------------
#     # Items CRUD
#     # ------------------------------------------
#
#     def add_item(self, confirmation_id: int, sku: str, name: str, quantity: int, item_status="OK"):
#         with self._get_conn() as conn:
#             cur = conn.cursor()
#             cur.execute("""
#                 INSERT INTO confirmation_items (confirmation_id, sku, name, quantity, item_status)
#                 VALUES (?, ?, ?, ?, ?)
#             """, (confirmation_id, sku, name, quantity, item_status))
#             conn.commit()
#             return cur.lastrowid
#
#     def get_items(self, confirmation_id: int):
#         with self._get_conn() as conn:
#             cur = conn.cursor()
#             cur.execute("""
#                 SELECT id, sku, name, quantity, item_status, created_at, updated_at
#                 FROM confirmation_items
#                 WHERE confirmation_id=?
#             """, (confirmation_id,))
#             return cur.fetchall()

# import sqlite3
# from datetime import datetime, timezone
# from Common.settings import DB_PATH
#
#
# class ConfirmationsRepository:
#     """
#     Репозиторий для работы с таблицами confirmations и confirmation_items.
#     Надёжный слой поверх sqlite: WAL + timeout + foreign_keys.
#     """
#
#     def __init__(self, db_path=DB_PATH):
#         self.db_path = db_path
#         self._init_db()   # инициализация (создание таблиц + включение WAL)
#
#     # ------------------------------------------
#     # Подключение
#     # ------------------------------------------
#
#     def _get_conn(self):
#         """
#         Создаёт подключение с повышенной надёжностью:
#         - timeout = 30 сек (ожидание освобождения БД)
#         - row_factory = sqlite3.Row (удобные результаты)
#         - foreign_keys = ON (строгая целостность)
#         """
#         conn = sqlite3.connect(self.db_path, timeout=30)
#         conn.row_factory = sqlite3.Row
#
#         cur = conn.cursor()
#         cur.execute("PRAGMA foreign_keys = ON;")
#         # synchronous = NORMAL — лучший баланс (быстрее, надёжно)
#         cur.execute("PRAGMA synchronous = NORMAL;")
#         return conn
#
#
#     def _row_to_dict(self, row: sqlite3.Row) -> dict:
#         return {k: row[k] for k in row.keys()}
#
#
#     # ------------------------------------------
#     # Инициализация базы (один раз)
#     # ------------------------------------------
#
#     def _init_db(self):
#         """
#         Выполняется при старте:
#         - включает WAL (хранится в файле БД, достаточно сделать 1 раз)
#         - создаёт таблицы
#         """
#         with sqlite3.connect(self.db_path) as conn:
#             cur = conn.cursor()
#
#             # Включаем WAL (возвращает режим, можно проверить)
#             cur.execute("PRAGMA journal_mode = WAL;")
#
#             # Создание таблиц
#             cur.execute("""
#                 CREATE TABLE IF NOT EXISTS confirmations (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     posting_number TEXT NOT NULL UNIQUE,
#                     status TEXT NOT NULL,
#                     error_message TEXT,
#                     created_at TEXT NOT NULL,
#                     updated_at TEXT NOT NULL
#                 )
#             """)
#
#             cur.execute("""
#                 CREATE TABLE IF NOT EXISTS confirmation_items (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     confirmation_id INTEGER NOT NULL,
#                     sku TEXT NOT NULL,
#                     name TEXT,
#                     quantity INTEGER NOT NULL,
#                     item_status TEXT DEFAULT 'OK',
#                     created_at TEXT NOT NULL,
#                     updated_at TEXT NOT NULL,
#
#                     FOREIGN KEY (confirmation_id)
#                         REFERENCES confirmations(id)
#                         ON DELETE CASCADE
#                 )
#             """)
#
#             conn.commit()
#
#     # ------------------------------------------
#     # Confirmations CRUD
#     # ------------------------------------------
#
#     def add_confirmation(self, posting_number: str, status: str = "NEW") -> int:
#         now = datetime.now(timezone.utc).isoformat(timespec="seconds")
#         with self._get_conn() as conn:
#             cur = conn.cursor()
#             cur.execute("""
#                 INSERT INTO confirmations (posting_number, status, created_at, updated_at)
#                 VALUES (?, ?, ?, ?)
#             """, (posting_number, status, now, now))
#             conn.commit()
#             return cur.lastrowid
#
#     def update_status(self, posting_number: str, new_status: str, error_message: str | None = None):
#         now = datetime.now(timezone.utc).isoformat(timespec="seconds")
#
#         with self._get_conn() as conn:
#             cur = conn.cursor()
#             cur.execute("""
#                 UPDATE confirmations
#                 SET status=?, error_message=?, updated_at=?
#                 WHERE posting_number=?
#             """, (new_status, error_message, now, posting_number))
#             conn.commit()
#
#     def get_by_posting(self, posting_number: str):
#         with self._get_conn() as conn:
#             cur = conn.cursor()
#             cur.execute("""
#                 SELECT id, posting_number, status, created_at, updated_at
#                 FROM confirmations
#                 WHERE posting_number = ?
#             """, (posting_number,))
#             return cur.fetchone()
#
#     def get_all(self):
#         with self._get_conn() as conn:
#             cur = conn.cursor()
#             cur.execute("""
#                 SELECT id, posting_number, status, error_message ,created_at, updated_at
#                 FROM confirmations
#                 ORDER BY id DESC
#             """)
#             rows = cur.fetchall()
#             return [self._row_to_dict(r) for r in rows]
#
#     def delete_confirmation(self, posting_number: str):
#         with self._get_conn() as conn:
#             cur = conn.cursor()
#             cur.execute("DELETE FROM confirmations WHERE posting_number = ?", (posting_number,))
#             conn.commit()
#
#     def get_by_status(self, status: str):
#         with self._get_conn() as conn:
#             cur = conn.cursor()
#             cur.execute("""
#                 SELECT id, posting_number, status, error_message, created_at, updated_at
#                 FROM confirmations
#                 WHERE status = ?
#                 ORDER BY id DESC
#             """, (status,))
#             rows = cur.fetchall()
#             return [self._row_to_dict(r) for r in rows]
#
#     # ------------------------------------------
#     # Items CRUD
#     # ------------------------------------------
#
#     def add_item(self, confirmation_id: int, sku: str, name: str, quantity: int, item_status="OK"):
#         with self._get_conn() as conn:
#             cur = conn.cursor()
#             cur.execute("""
#                 INSERT INTO confirmation_items (confirmation_id, sku, name, quantity, item_status)
#                 VALUES (?, ?, ?, ?, ?)
#             """, (confirmation_id, sku, name, quantity, item_status))
#             conn.commit()
#             return cur.lastrowid
#
#     def get_items(self, confirmation_id: int):
#         with self._get_conn() as conn:
#             cur = conn.cursor()
#             cur.execute("""
#                 SELECT id, sku, name, quantity, item_status, created_at, updated_at
#                 FROM confirmation_items
#                 WHERE confirmation_id = ?
#             """, (confirmation_id,))
#             return cur.fetchall()


import sqlite3
from datetime import datetime, timezone
from Common.settings import DB_PATH

class ConfirmationsRepository:
    """
    Репозиторий для работы с таблицами confirmations и confirmation_items.
    ORM-заменитель на sqlite.
    Даты хранятся в ISO 8601 UTC.
    """

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    # ------------------------------------------
    # Подключение к БД
    # ------------------------------------------

    def _get_conn(self):
        """
        Создаёт подключение с повышенной надёжностью:
        - timeout = 30 сек (ожидание освобождения БД)
        - row_factory = sqlite3.Row (удобные результаты)
        - foreign_keys = ON (строгая целостность)
        """
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row

        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON;")
        cur.execute("PRAGMA synchronous = NORMAL;")
        return conn

    # ------------------------------------------
    # Инициализация БД
    # ------------------------------------------

    def _init_db(self):
        """
        Выполняется при старте:
        - включает WAL (хранится в файле БД, достаточно сделать 1 раз)
        - создаёт таблицы
        """
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()

            # Включаем WAL
            cur.execute("PRAGMA journal_mode = WAL;")

            # Таблица confirmations
            cur.execute("""
                CREATE TABLE IF NOT EXISTS confirmations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    posting_number TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Таблица confirmation_items
            cur.execute("""
                CREATE TABLE IF NOT EXISTS confirmation_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    confirmation_id INTEGER NOT NULL,
                    sku TEXT NOT NULL,
                    name TEXT,
                    quantity INTEGER NOT NULL,
                    item_status TEXT DEFAULT 'OK',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (confirmation_id)
                        REFERENCES confirmations(id)
                        ON DELETE CASCADE
                )
            """)
            conn.commit()

    # ------------------------------------------
    # Вспомогательные методы
    # ------------------------------------------

    @staticmethod
    def _now_iso() -> str:
        """Возвращает текущий UTC timestamp в ISO 8601 без микросекунд"""
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        """Преобразует sqlite3.Row в обычный словарь"""
        return {k: row[k] for k in row.keys()}

    # ------------------------------------------
    # Confirmations CRUD
    # ------------------------------------------

    def add_confirmation(self, posting_number: str, status: str = "NEW") -> int:
        now = self._now_iso()
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO confirmations (posting_number, status, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (posting_number, status, now, now))
            conn.commit()
            return cur.lastrowid

    def update_status(self, posting_number: str, new_status: str, error_message: str | None = None):
        now = self._now_iso()
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE confirmations
                SET status=?, error_message=?, updated_at=?
                WHERE posting_number=?
            """, (new_status, error_message, now, posting_number))
            conn.commit()

    def get_by_posting(self, posting_number: str) -> dict | None:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM confirmations
                WHERE posting_number=?
            """, (posting_number,))
            row = cur.fetchone()
            return self._row_to_dict(row) if row else None

    def get_all(self) -> list[dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM confirmations
                ORDER BY id DESC
            """)
            return [self._row_to_dict(r) for r in cur.fetchall()]

    def get_by_status(self, status: str) -> list[dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM confirmations
                WHERE status=?
                ORDER BY id DESC
            """, (status,))
            return [self._row_to_dict(r) for r in cur.fetchall()]

    def get_list_postings_numbers_by_status(self, status: str) -> list[dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT posting_number FROM confirmations
                WHERE status=?
                ORDER BY id DESC
            """, (status,))
            return [self._row_to_dict(r) for r in cur.fetchall()]

    def delete_confirmation(self, posting_number: str):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM confirmations WHERE posting_number=?", (posting_number,))
            conn.commit()

    # ------------------------------------------
    # Items CRUD
    # ------------------------------------------

    def add_item(self, confirmation_id: int, sku: str, name: str, quantity: int, item_status="OK") -> int:
        now = self._now_iso()
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO confirmation_items
                (confirmation_id, sku, name, quantity, item_status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (confirmation_id, sku, name, quantity, item_status, now, now))
            conn.commit()
            return cur.lastrowid

    def get_items(self, confirmation_id: int) -> list[dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM confirmation_items
                WHERE confirmation_id=?
            """, (confirmation_id,))
            return [self._row_to_dict(r) for r in cur.fetchall()]
