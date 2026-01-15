import sqlite3
import tempfile

from Confirmations.api.exemplar_status.ozon_gtd_preparation_service import (
    OzonGtdPreparationService
)

def test_prepare_full_flow():
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

        ship_not_available = {
            "x": {
                "posting_number": "POST-1",
                "products": [
                    {
                        "product_id": 100,
                        "exemplars": [
                            {"exemplar_id": 111}
                        ],
                    }
                ],
            }
        }

        service = OzonGtdPreparationService(None, tmp.name)
        payloads = service.prepare(ship_not_available)

        assert payloads == [
            {
                "posting_number": "POST-1",
                "products": [
                    {
                        "product_id": 100,
                        "exemplars": [
                            {
                                "exemplar_id": 111,
                                "gtd": "GTD-123",
                            }
                        ],
                    }
                ],
            }
        ]
