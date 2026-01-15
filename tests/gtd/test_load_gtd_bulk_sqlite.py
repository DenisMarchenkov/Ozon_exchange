import sqlite3
import tempfile

from Confirmations.api.exemplar_status.ozon_gtd_preparation_service import (
    OzonGtdPreparationService
)

def test_load_gtd_bulk_from_sqlite():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        conn = sqlite3.connect(tmp.name)
        cur = conn.cursor()

        cur.executescript("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                posting_number TEXT
            );

            CREATE TABLE order_items (
                order_id INTEGER,
                product_id INTEGER,
                offer_id TEXT
            );

            CREATE TABLE confirmation_items (
                sku_art TEXT,
                gtd TEXT
            );

            INSERT INTO orders VALUES (1, 'POST-1');
            INSERT INTO order_items VALUES (1, 100, 'SKU-1');
            INSERT INTO confirmation_items VALUES ('SKU-1', 'GTD-123');
        """)
        conn.commit()
        conn.close()

        service = OzonGtdPreparationService(None, tmp.name)

        exemplars = [
            {"posting_number": "POST-1", "product_id": 100, "exemplar_id": 111}
        ]

        gtd_map = service._load_gtd_bulk(exemplars)

        assert gtd_map == {
            ("POST-1", 100): "GTD-123"
        }
