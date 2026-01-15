from typing import Optional
from sqlite3 import Row
from Common.db.database import Database


class SupplierPriceHashRepository:
    """
    Репозиторий для работы с хешами файлов поставщиков и рассчитанными ценами.
    Использует класс Database для работы с SQLite.
    """

    def __init__(self, db: Database):
        self.db = db

    # ------------------------------
    # Хеши файлов поставщика
    # ------------------------------
    def get_last_hash(self, supplier_id: int) -> Optional[str]:
        """Возвращает последний хеш прайса поставщика"""
        with self.db.connect() as conn:
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
        """Проверяет, был ли уже такой хеш"""
        with self.db.connect() as conn:
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
            exists = cur.fetchone() is not None
        return exists

    def save_hash(self, metadata: dict, supplier_id: int, created_at: str) -> int:
        """Сохраняет хеш файла поставщика"""
        with self.db.connect() as conn:
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

    def get_all(self) -> list[dict]:
        """Возвращает все файлы поставщиков"""
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM supplier_prices")
            rows = cur.fetchall()
        return [self._row_to_dict(r) for r in rows]

    # ------------------------------
    # Расчёт цен
    # ------------------------------
    def save_price_calculation(
        self,
        supplier_price_id: int,
        sku_art: str,
        supplier_price: float,
        calc: dict,
        created_at: str,
    ) -> None:
        """Сохраняет рассчитанную цену по SKU"""
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
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
                """,
                (
                    supplier_price_id,
                    sku_art,
                    supplier_price,
                    calc["min_price"],
                    calc["price"],
                    calc["old_price"],
                    int(calc["manual"]),
                    created_at,
                ),
            )
            conn.commit()

    # ------------------------------
    # Вспомогательные методы
    # ------------------------------
    @staticmethod
    def _row_to_dict(row: Row) -> dict:
        return {k: row[k] for k in row.keys()}
