from typing import Optional
from sqlite3 import Row
from Common.db.database import Database


class PricesRepository:
    """
    Репозиторий для работы с хешами файлов поставщиков, файла наценок и результатами расчётов.
    """

    def __init__(self, db: Database):
        self.db = db

    # ------------------------------
    # Вспомогательные методы
    # ------------------------------
    @staticmethod
    def _row_to_dict(row: Row) -> dict:
        return {k: row[k] for k in row.keys()}

    # ------------------------------
    # Файлы поставщиков (supplier_prices)
    # ------------------------------
    def get_last_supplier_hash(self, supplier_id: int) -> Optional[str]:
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

    def get_last_supplier_price_id(self, supplier_id: int) -> Optional[int]:
        """Возвращает ID последней записи файла поставщика"""
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id
                FROM supplier_prices
                WHERE supplier_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (supplier_id,),
            )
            row = cur.fetchone()
        return row[0] if row else None

    def save_supplier_price(self, metadata: dict, supplier_id: int, created_at: str) -> int:
        """Сохраняет метаданные и хеш файла поставщика"""
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO supplier_prices (
                    name, file_hash, file_size,
                    row_count, columns,
                    supplier_id, total_qty,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    metadata["name"],
                    metadata["file_hash"],
                    metadata["file_size"],
                    metadata["row_count"],
                    metadata["columns"],
                    supplier_id,
                    metadata.get("total_qty") or 0,
                    created_at,
                ),
            )
            conn.commit()
            return cur.lastrowid

    # ------------------------------
    # Файлы наценок (markup_files)
    # ------------------------------
    def get_last_markup_hash(self) -> Optional[str]:
        """Возвращает последний хеш файла наценок"""
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT file_hash
                FROM markup_files
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()
        return row[0] if row else None

    def get_last_markup_file_id(self) -> Optional[int]:
        """Возвращает ID последней записи файла наценок"""
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id
                FROM markup_files
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()
        return row[0] if row else None

    def save_markup_file(self, metadata: dict, created_at: str) -> int:
        """Сохраняет метаданные и хеш файла наценок"""
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO markup_files (
                    name, file_hash, file_size,
                    row_count, columns,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    metadata["name"],
                    metadata["file_hash"],
                    metadata["file_size"],
                    metadata["row_count"],
                    metadata["columns"],
                    created_at,
                ),
            )
            conn.commit()
            return cur.lastrowid

    # ------------------------------
    # Расчёт цен (price_calculations)
    # ------------------------------
    def save_price_calculation(
        self,
        supplier_price_id: int,
        markup_file_id: int,
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
                    markup_file_id,
                    sku_art,
                    supplier_price,
                    min_price,
                    price,
                    old_price,
                    manual,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    supplier_price_id,
                    markup_file_id,
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

    def get_all_supplier_prices(self) -> list[dict]:
        """Возвращает все записи файлов поставщиков"""
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM supplier_prices")
            rows = cur.fetchall()
        return [self._row_to_dict(r) for r in rows]

