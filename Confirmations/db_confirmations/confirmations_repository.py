import sqlite3
from typing import List, Dict
from Common.settings import DB_PATH


class ConfirmationsRepository:
    """
    Репозиторий для работы с confirmations и confirmation_items.
    Поддерживает CRUD для подтверждений и их позиций.
    """

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

    # ------------------------------
    # Инициализация таблиц
    # ------------------------------
    def _init_db(self):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA foreign_keys = ON;")
            cur.execute("PRAGMA journal_mode = WAL;")
            cur.execute("PRAGMA synchronous = NORMAL;")

            # Таблица подтверждений
            cur.execute("""
                CREATE TABLE IF NOT EXISTS confirmations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    posting_number TEXT NOT NULL UNIQUE,
                    division_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    source_file TEXT,
                    stickers TEXT DEFAULT 'not_ready',
                    stickers_error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Таблица позиций подтверждений
            cur.execute("""
                CREATE TABLE IF NOT EXISTS confirmation_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    confirmation_id INTEGER NOT NULL,
                    sku_code INTEGER NOT NULL,
                    sku_art TEXT NOT NULL,
                    name TEXT,
                    quantity_confirm INTEGER NOT NULL,
                    quantity_refused INTEGER NOT NULL,
                    item_status TEXT NOT NULL,
                    price_with_vat REAL,
                    gtd TEXT,
                    date_expiration TEXT,
                    brand TEXT,
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
    def _row_to_dict(row: sqlite3.Row) -> dict:
        return {k: row[k] for k in row.keys()}

    # ------------------------------
    # CRUD: Confirmations
    # ------------------------------
    def add_confirmation(
        self,
        posting_number: str,
        division_id: int,
        status: str,
        source_file: str | None,
        created_at: str,
        updated_at: str
    ) -> int:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO confirmations
                (posting_number, division_id, status, source_file, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (posting_number, division_id, status, source_file, created_at, updated_at))
            return cur.lastrowid

    def get_by_posting(self, posting_number: str) -> Dict | None:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM confirmations WHERE posting_number=?", (posting_number,))
            row = cur.fetchone()
            return dict(row) if row else None

    def update_status(self, posting_number: str, status: str, updated_at: str):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE confirmations
                SET status=?, updated_at=?
                WHERE posting_number=?
            """, (status, updated_at, posting_number))
            conn.commit()

    def get_list_postings_numbers_by_status(self, status: str) -> list[str]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT posting_number
                FROM confirmations
                WHERE status = ?
            """, (status,))
            rows = cur.fetchall()
            return [row["posting_number"] for row in rows]

    def get_all(self) -> list[dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM confirmations
                ORDER BY id DESC
            """)
            return [self._row_to_dict(r) for r in cur.fetchall()]

    # ------------------------------
    # CRUD: Confirmation Items
    # ------------------------------
    def delete_items_by_confirmation(self, confirmation_id: int):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM confirmation_items WHERE confirmation_id=?", (confirmation_id,))
            conn.commit()

    def add_items_bulk(self, items: List[tuple]):
        if not items:
            return
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.executemany("""
                INSERT INTO confirmation_items
                (confirmation_id, sku_code, sku_art, name, quantity_confirm,
                 quantity_refused, item_status, price_with_vat,
                 gtd, date_expiration, brand, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, items)
            conn.commit()

    def get_items_by_statuses(
            self,
            confirmation_status: str,
            item_status: str,
    ) -> list[dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    ci.*,
                    c.id AS confirmation_id,
                    c.posting_number,
                    c.division_id
                FROM confirmation_items AS ci
                JOIN confirmations AS c
                    ON ci.confirmation_id = c.id
                WHERE c.status = ?
                  AND ci.item_status = ?
            """, (confirmation_status, item_status))
            return [self._row_to_dict(r) for r in cur.fetchall()]

    def get_items_for_error_mailer(self, status: str) -> list[dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT ci.*, c.id AS confirmation_id, c.posting_number, c.error_message, c.division_id
                FROM confirmation_items AS ci
                JOIN confirmations AS c
                    ON ci.confirmation_id = c.id
                WHERE c.status = ?
            """, (status,))
            return [self._row_to_dict(r) for r in cur.fetchall()]

    def get_all_items(self) -> list[dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM confirmation_items
                ORDER BY id DESC
            """)
            return [self._row_to_dict(r) for r in cur.fetchall()]

    # ------------------------------
    # Методы для работы с Ozon labels
    # ------------------------------
    def get_postings_by_status_and_stickers_status(self, status: str, sticker_status: str) -> List[str]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT c.posting_number
                FROM confirmations c
                LEFT JOIN confirmation_items ci ON ci.confirmation_id = c.id
                WHERE c.status=? AND c.stickers=?
            """, (status, sticker_status))
            rows = cur.fetchall()
            return [row["posting_number"] for row in rows]

    # TODO разобраться с error: str | None = None, параметр error ни куда не передается
    def update_stickers_status(self, postings: List[str], status: str, error: str | None = None):
        with self._get_conn() as conn:
            cur = conn.cursor()
            for posting_number in postings:
                cur.execute("""
                    UPDATE confirmations
                    SET stickers=?, updated_at=CURRENT_TIMESTAMP
                    WHERE posting_number=?
                """, (status, posting_number))
            conn.commit()

    def get_items_for_warehouse(self, status: str, sticker_status: str) -> List[Dict]:
        # TODO передаем не верные данные в date_order и date_ship, нужно исправить
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    c.posting_number,
                    c.created_at AS date_order,
                    c.updated_at AS date_ship,
                    ci.sku_art,
                    ci.name,
                    ci.quantity_confirm,
                    ci.price_with_vat,
                    ci.date_expiration,
                    ci.brand
                FROM confirmation_items ci
                JOIN confirmations c ON c.id = ci.confirmation_id
                WHERE c.status=? AND c.stickers=?
            """, (status, sticker_status))
            return [dict(row) for row in cur.fetchall()]
