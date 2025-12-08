from Common.db import get_connection


def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                posting_number TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def get_order_status(posting_number: str) -> str | None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status FROM orders WHERE posting_number = ?",
            (posting_number,)
        )
        row = cursor.fetchone()
        return row[0] if row else None


def create_order(posting_number: str, status: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO orders (posting_number, status)
            VALUES (?, ?)
        """, (posting_number, status))
        conn.commit()


def update_order_status(posting_number: str, new_status: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE orders
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE posting_number = ?
        """, (new_status, posting_number))
        conn.commit()
