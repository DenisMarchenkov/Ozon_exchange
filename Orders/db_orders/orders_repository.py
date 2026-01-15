import sqlite3
from typing import Optional

class OrdersRepository:

    def __init__(self, db):
        self.db = db


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
        with self.db.connect() as conn:
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
        with self.db.connect() as conn:
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


    # ---------- READ ----------
    def get_status(self, posting_number: str) -> Optional[str]:
        """
        Возвращает статус заказа по posting_number.
        """
        with self.db.connect() as conn:
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
        with self.db.connect() as conn:
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
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id
                FROM orders
                WHERE posting_number = ?
            """, (posting_number,))
            row = cursor.fetchone()
            return row["id"] if row else None

    def get_all_orders(self):
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT *
                FROM orders
            """,)
            return [self._row_to_dict(r) for r in cursor.fetchall()]

    def get_all_requirements(self):
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT *
                FROM order_requirements
            """,)
            return [self._row_to_dict(r) for r in cursor.fetchall()]

    def get_all_items(self):
        with self.db.connect() as conn:
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
        with self.db.connect() as conn:
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
        with self.db.connect() as conn:
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
        with self.db.connect() as conn:
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