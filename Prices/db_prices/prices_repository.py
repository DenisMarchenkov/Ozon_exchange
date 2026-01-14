import sqlite3
from typing import Optional


class SupplierPriceHashRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

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

            cur.execute("""
            CREATE TABLE IF NOT EXISTS supplier_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                row_count INTEGER NOT NULL,
                columns TEXT NOT NULL,
                supplier_id INTEGER NOT NULL,
                total_qty INTEGER NOT NULL,
                created_at TEXT NOT NULL
                )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS price_calculations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            supplier_price_id INTEGER NOT NULL,   -- связь с файлом поставщика
            sku_art TEXT NOT NULL,
        
            supplier_price REAL NOT NULL,
        
            min_price REAL NOT NULL,
            price REAL NOT NULL,
            old_price REAL NOT NULL,
        
            manual INTEGER NOT NULL,               -- 0 / 1
            created_at TEXT NOT NULL,
        
            FOREIGN KEY (supplier_price_id)
                REFERENCES supplier_prices(id)
                ON DELETE CASCADE
            )
        """)


    def get_last_hash(self, supplier_id: int) -> Optional[str]:
        """
        Возвращает последний хеш прайса поставщика
        """
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT file_hash
                FROM supplier_prices
                WHERE supplier_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (supplier_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None

    def exists(self, supplier_id: int, file_hash: str) -> bool:
        """
        Проверяет, был ли уже такой хеш
        """
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT 1
                FROM supplier_prices
                WHERE supplier_id = ? AND file_hash = ?
                LIMIT 1
                """,
                (supplier_id, file_hash),
            )
            return cur.fetchone() is not None

    def save_hash(self, metadata: dict, supplier_id: int, created_at: str) -> None:
        """
        Сохраняет хеш файла поставщика
        """
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO supplier_prices
                (name, file_hash, file_size, row_count, columns, total_qty, supplier_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    metadata["name"],
                    metadata["file_hash"],
                    metadata["file_size"],
                    metadata["row_count"],
                    metadata["columns"],
                    metadata["total_qty"],
                    supplier_id,
                    created_at,
                ),
            )
            conn.commit()
            return cur.lastrowid

    def get_all(self):

        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT *
                FROM supplier_prices
                """)
        return [self._row_to_dict(r) for r in cur.fetchall()]

    def save_price_calculation(
            self,
            supplier_price_id: int,
            sku_art: str,
            supplier_price: float,
            calc: dict,
            created_at: str,
    ):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO price_calculations (
                    supplier_price_id,
                    sku_art,
                    supplier_price,
                    min_price,
                    price,
                    old_price,
                    manual,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                supplier_price_id,
                sku_art,
                supplier_price,
                calc["min_price"],
                calc["price"],
                calc["old_price"],
                int(calc["manual"]),
                created_at,
            ))

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        return {k: row[k] for k in row.keys()}
