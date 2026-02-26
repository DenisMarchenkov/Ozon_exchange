import sqlite3
from typing import List, Dict, Iterable
from datetime import datetime, timezone


class ConfirmationsRepository:
    """
    Репозиторий для работы с confirmations и confirmation_items.

    Dispatch считается агрегатом:
    confirmations привязываются к dispatch через confirmations.dispatch_id
    """

    def __init__(self,  db=None):
        if db is None:
            from Common.settings import DB_PATH
            from Common.db.database import Database
            db = Database(DB_PATH)
        self.db = db

    # ------------------------------
    # Helpers
    # ------------------------------
    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        return {k: row[k] for k in row.keys()}

    @staticmethod
    def _now() -> str:
        #return datetime.utcnow().isoformat()
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    # ------------------------------
    # CRUD: Confirmations
    # ------------------------------
    def add_confirmation(
        self,
        posting_number: str,
        division_id: int,
        status: str,
        source_file: str | None,
        ordered_at: str | None,
        shipped_at: str | None,
        created_at: str,
        updated_at: str,
        marketplace_status: str
    ) -> int:
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO confirmations
                (posting_number, division_id, status, source_file, ordered_at, shipped_at, created_at, updated_at, marketplace_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (posting_number, division_id, status, source_file, ordered_at, shipped_at, created_at, updated_at, marketplace_status))
            conn.commit()
            return cur.lastrowid

    def get_by_posting(self, posting_number: str) -> Dict | None:
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM confirmations
                WHERE posting_number = ?
            """, (posting_number,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_by_status(self, status: str) -> List[Dict]:
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT * FROM confirmations
                WHERE status = ?
                """,
                (status,)
            )
            return [dict(row) for row in cur.fetchall()]

    def get_by_statuses(self, statuses: Iterable[str]) -> List[Dict]:
        statuses = list(statuses)
        if not statuses:
            return []

        placeholders = ",".join("?" for _ in statuses)

        query = f"""
            SELECT *
            FROM confirmations
            WHERE status IN ({placeholders})
            AND marketplace_status NOT IN ('cancelled', 'delivered')
        """

        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute(query, statuses)
            return [dict(row) for row in cur.fetchall()]


    def update_status(self, posting_number: str, status: str):
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE confirmations
                SET status = ?, updated_at = ?
                WHERE posting_number = ?
            """, (status, self._now(), posting_number))
            conn.commit()

    # ------------------------------
    # 🔒 Dispatch logic (НОВОЕ)
    # ------------------------------
    def lock_postings_for_dispatch(self, dispatch_id: str, divisions: tuple = None) -> List[str]:
        """
        Атомарно закрепляет postings за dispatch.
        Повторный вызов безопасен.
        """
        now = self._now()

        with self.db.connect() as conn:
            cur = conn.cursor()

            if divisions:
                placeholders = ",".join("?" for _ in divisions)
                query = f"""
                    UPDATE confirmations
                    SET
                        dispatch_id = ?,
                        status = 'IN_DISPATCH',
                        updated_at = ?
                    WHERE id IN (
                        SELECT id
                        FROM confirmations
                        WHERE status = 'awaiting_delivery'
                          AND stickers = 'not_ready'
                          AND dispatch_id IS NULL
                          AND division_id IN ({placeholders})
                    )
                    RETURNING posting_number;
                """
                params = [dispatch_id, now, *divisions]
            else:
                query = """
                    UPDATE confirmations
                    SET
                        dispatch_id = ?,
                        status = 'IN_DISPATCH',
                        updated_at = ?
                    WHERE id IN (
                        SELECT id
                        FROM confirmations
                        WHERE status = 'awaiting_delivery'
                          AND stickers = 'not_ready'
                          AND dispatch_id IS NULL
                    )
                    RETURNING posting_number;
                """
                params = [dispatch_id, now]

            cur.execute(query, params)

            rows = cur.fetchall()
            conn.commit()

        return [row["posting_number"] for row in rows]

    def remove_postings_from_dispatch(self, postings: list[str]):
        """
        Исключает postings из dispatch (сбрасывает dispatch_id).
        """
        if not postings:
            return

        with self.db.connect() as conn:
            cur = conn.cursor()
            placeholders = ",".join("?" for _ in postings)
            cur.execute(f"""
                UPDATE confirmations
                SET dispatch_id = NULL,
                    status = 'awaiting_delivery',
                    stickers = 'not_ready',
                    updated_at = ?
                WHERE posting_number IN ({placeholders})
            """, (self._now(), *postings))
            conn.commit()

    def lock_specific_postings(self, dispatch_id: str, postings: list[str]) -> list[str]:
        if not postings:
            return []

        with self.db.connect() as conn:
            cur = conn.cursor()
            now = self._now()

            cur.execute(
                f"""
                UPDATE confirmations
                SET dispatch_id = ?, status = 'IN_DISPATCH', updated_at = ?
                WHERE posting_number IN ({','.join(['?'] * len(postings))})
                """,
                [dispatch_id, now, *postings]
            )
            conn.commit()
            return postings

    def get_postings_by_dispatch(self, dispatch_id: str) -> List[str]:
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT posting_number
                FROM confirmations
                WHERE dispatch_id = ?
                ORDER BY posting_number
            """, (dispatch_id,))
            return [row["posting_number"] for row in cur.fetchall()]

    def get_items_by_dispatch(self, dispatch_id: str) -> List[Dict]:
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    c.division_id,
                    c.posting_number,
                    c.ordered_at,
                    c.shipped_at,
                    ci.sku_art,
                    ci.name,
                    ci.quantity_confirm,
                    ci.price_with_vat,
                    ci.date_expiration,
                    ci.brand
                FROM confirmation_items ci
                JOIN confirmations c ON c.id = ci.confirmation_id
                WHERE c.dispatch_id = ?
                ORDER BY c.posting_number, ci.id
            """, (dispatch_id,))
            return [self._row_to_dict(r) for r in cur.fetchall()]

    def mark_dispatch_prepared(self, dispatch_id: str):
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE confirmations
                SET status = 'READY_FOR_SHIPMENT',
                    updated_at = ?
                WHERE dispatch_id = ?
            """, (self._now(), dispatch_id))
            conn.commit()


    # ------------------------------
    # CRUD: Confirmation Items
    # ------------------------------
    def delete_items_by_confirmation(self, confirmation_id: int):
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                DELETE FROM confirmation_items
                WHERE confirmation_id = ?
            """, (confirmation_id,))
            conn.commit()

    def add_items_bulk(self, items: List[tuple]):
        if not items:
            return
        with self.db.connect() as conn:
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

    def get_items_for_postings(
            self,
            posting_numbers: list[str],

    ) -> list[dict]:
        if not posting_numbers:
            return []

        placeholders = ",".join("?" for _ in posting_numbers)

        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute(f"""
                SELECT ci.*, c.posting_number, c.created_at, c.shipped_at
                FROM confirmation_items ci
                JOIN confirmations c ON c.id = ci.confirmation_id
                WHERE c.posting_number IN ({placeholders})
            """, (*posting_numbers,))

            return [dict(row) for row in cur.fetchall()]

    def get_items_for_posting(self, posting_number: str) -> list[dict]:
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT ci.*
            FROM confirmation_items ci
            JOIN confirmations c ON c.id = ci.confirmation_id
            WHERE c.posting_number = ?
            """, (posting_number,))
            return [dict(row) for row in cur.fetchall()]

    def get_list_postings_numbers_by_status(self, status: str) -> list[str]:
        with self.db.connect() as conn:
                    cur = conn.cursor()
                    cur.execute("""
                        SELECT posting_number
                        FROM confirmations
                        WHERE status = ?
                    """, (status,))
                    rows = cur.fetchall()
                    return [row["posting_number"] for row in rows]

    def get_items_for_error_mailer(self, status: str) -> list[dict]:
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT ci.*, c.id AS confirmation_id, c.posting_number, c.error_message, c.division_id
                FROM confirmation_items AS ci
                JOIN confirmations AS c
                    ON ci.confirmation_id = c.id
                WHERE c.status = ?
            """, (status,))
            return [self._row_to_dict(r) for r in cur.fetchall()]

    def get_all_items(self):
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT *
            FROM confirmation_items
            """)
            return [self._row_to_dict(r) for r in cur.fetchall()]

    # ------------------------------
    # ⚠️ DEPRECATED (оставлено для совместимости)
    # ------------------------------
    def get_postings_by_status_and_stickers_status(self, status: str, stickers_status: str) -> List[str]:
        """
        DEPRECATED: использовать lock_postings_for_dispatch
        """
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT posting_number
                FROM confirmations
                WHERE status = ? AND stickers = ? AND dispatch_id IS NULL
            """, (status, stickers_status))
            return [row["posting_number"] for row in cur.fetchall()]

    def get_items_for_warehouse(self, status: str, sticker_status: str) -> List[Dict]:
        """
        DEPRECATED: использовать get_items_by_dispatch
        """
        with self.db.connect() as conn:
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
                WHERE c.status = ? AND c.stickers = ?
            """, (status, sticker_status))
            return [dict(row) for row in cur.fetchall()]

    def get_items_by_statuses_conf_and_item(
            self,
            confirmation_status: str,
            item_status: str,
    ) -> list[dict]:
        with self.db.connect() as conn:
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

    def get_all(self) -> list[dict]:
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM confirmations
                ORDER BY id DESC
            """)
            return [self._row_to_dict(r) for r in cur.fetchall()]

    def update_stickers_status(self, postings: List[str], status: str, time):
        with self.db.connect() as conn:
            cur = conn.cursor()
            for posting_number in postings:
                cur.execute("""
                    UPDATE confirmations
                    SET stickers=?, updated_at=?
                    WHERE posting_number=?
                """, (status, time, posting_number))
            conn.commit()

    def mark_items_shortage_notified(self, item_ids: list[int]) -> None:
        if not item_ids:
            return

        now = self._now()

        with self.db.connect() as conn:
            cur = conn.cursor()

            placeholders = ",".join("?" for _ in item_ids)

            cur.execute(f"""
                UPDATE confirmation_items
                SET item_status = ?,
                    updated_at = ?
                WHERE id IN ({placeholders})
            """, ["SHORTAGE_NOTICE_SENT", now, *item_ids])

            conn.commit()
