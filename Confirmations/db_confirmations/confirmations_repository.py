import sqlite3

from typing import Any
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
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()

            cur.execute("PRAGMA journal_mode = WAL;")

            cur.execute("""
                CREATE TABLE IF NOT EXISTS confirmations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    posting_number TEXT NOT NULL UNIQUE,
                    division_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    source_file TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    stickers TEXT DEFAULT 'not_ready',
                    stickers_error TEXT
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS confirmation_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    confirmation_id INTEGER NOT NULL,
                    sku_code INTEGER NOT NULL,
                    sku_art TEXT NOT NULL,
                    name TEXT,
                    quantity_confirm INTEGER NOT NULL,
                    quantity_refused INTEGER NOT NULL,
                    item_status TEXT DEFAULT 'OK',
                    price_with_vat FLOAT NOT NULL,
                    date_expiration TEXT NOT NULL,
                    gtd TEXT NOT NULL,
                    brand TEXT NOT NULL,
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


    # ------------------------------------------
    # Confirmations CRUD
    # ------------------------------------------

    def add_confirmation(
        self,
        posting_number: str,
        division_id: int,
        created_at: str,
        updated_at: str,
        status: str = "NEW",
        source_file: str | None = None
    ) -> int:
        #now = self._now_iso()
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO confirmations
                (posting_number, division_id, status, source_file, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (posting_number, division_id, status, source_file, created_at, updated_at))
            conn.commit()
            return cur.lastrowid

    def update_status(
        self,
        posting_number: str,
        new_status: str,
        updated_at: str,
        error_message: str | None = None
    ):
        #now = self._now_iso()
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE confirmations
                SET status=?, error_message=?, updated_at=?
                WHERE posting_number=?
            """, (new_status, error_message, updated_at, posting_number))
            conn.commit()

    def get_list_postings_numbers_by_status(self, status: str) -> list[Any]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT posting_number
                FROM confirmations
                WHERE status=?
            """, (status,))
            return [r["posting_number"] for r in cur.fetchall()]

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

    def get_by_posting(self, posting_number: str) -> dict | None:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM confirmations
                WHERE posting_number=?
            """, (posting_number,))
            row = cur.fetchone()
            return self._row_to_dict(row) if row else None

    def get_postings_by_status_and_stickers_status(self, status: str, sticker_status: str) -> list[str] | None:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT posting_number
            FROM confirmations
            WHERE status=?
            AND stickers=?
            """, (status, sticker_status))
            rows = cur.fetchall()
            return [row['posting_number'] for row in rows]


    # ------------------------------------------
    # Items CRUD
    # ------------------------------------------
    def add_items_bulk(self, items: list[tuple]):
        """
        items:
        (
            confirmation_id,
            sku_code,
            sku_art,
            name,
            quantity_confirm,
            quantity_refused,
            item_status,
            price_with_vat,
            gtd,
            date_expiration,
            brand,
            created_at,
            updated_at
        )
        """
        if not items:
            return

        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.executemany("""
                INSERT INTO confirmation_items
                (confirmation_id, sku_code, sku_art, name,
                 quantity_confirm, quantity_refused, item_status,
                 price_with_vat, gtd, date_expiration, brand,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, items)
            conn.commit()

    def get_all_items(self) -> list[dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM confirmation_items
                ORDER BY id DESC
            """)
            return [self._row_to_dict(r) for r in cur.fetchall()]

    def delete_items_by_confirmation(self, confirmation_id: int):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM confirmation_items WHERE confirmation_id=?",
                (confirmation_id,)
            )
            conn.commit()

    def get_items_by_posting_number(self, confirmation_id: int) -> list[dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM confirmation_items
                WHERE confirmation_id=?
            """, (confirmation_id,))
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

    def get_items_for_warehouse(self, confirmation_status: str, sticker_status: str) -> list[dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            # TODO передаем не верные данные в date_order и date_ship, нужно исправить
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
                JOIN confirmations c
                    ON ci.confirmation_id = c.id
                WHERE c.status = ?
                AND c.stickers = ?
            """, (confirmation_status, sticker_status))
            return [self._row_to_dict(r) for r in cur.fetchall()]

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

    # TODO нужно написать inspect_db.py в Common перенести в него
    def get_all_tables(self) -> list[str]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
            """)
            return [row[0] for row in cur.fetchall()]


    # ------------------------------------------
    # Items CRUD
    # ------------------------------------------
    def update_stickers_status(
            self,
            posting_numbers: list[str],
            status: str,
            error_message: str | None = None
    ):
        if not posting_numbers:
            return

        placeholders = ",".join("?" for _ in posting_numbers)

        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(f"""
                UPDATE confirmations
                SET
                    stickers = ?,
                    stickers_error = ?
                WHERE posting_number IN ({placeholders})
            """, [status, error_message, *posting_numbers])
            conn.commit()