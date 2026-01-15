def init_all(db):
    init_orders_schema(db)
    init_confirmations_schema(db)
    init_dispatch_schema(db)
    init_prices_schema(db)

def init_orders_schema(db):
    with db.connect() as conn:
        cur = conn.cursor()

        # ------------------------------
        # Таблица заказов
        # ------------------------------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                posting_number TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL,

                -- флаг наличия зависимостей
                has_requirements INTEGER DEFAULT 0,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        # ------------------------------
        # Таблица позиций в заказе
        # ------------------------------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                offer_id TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0),

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (order_id)
                    REFERENCES orders(id)
                    ON DELETE CASCADE
            )
        """)

        # ------------------------------
        # Индексы
        # ------------------------------
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_posting_number
            ON orders(posting_number)
        """)


        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_order_items_order_id
            ON order_items(order_id)
        """)

        conn.commit()

def init_confirmations_schema(db):
    with db.connect() as conn:
        cur = conn.cursor()

        # Confirmations (postings)
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
                           dispatch_id TEXT,
                           ordered_at TEXT,
                           shipped_at TEXT,
                           created_at TEXT NOT NULL,
                           updated_at TEXT NOT NULL
                       )
                   """)

        # Confirmation items
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


        # Индекс для lock_postings
        cur.execute("""
                       CREATE INDEX IF NOT EXISTS idx_confirmations_lock
                       ON confirmations(status, stickers, dispatch_id)
                   """)

        conn.commit()

def init_dispatch_schema(db):
    with db.connect() as conn:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS dispatch (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS dispatch_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dispatch_id TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                created_at TEXT,
                FOREIGN KEY(dispatch_id) REFERENCES dispatch(id) ON DELETE CASCADE,
                UNIQUE(dispatch_id, file_type)
            )
        """)

        conn.commit()

def init_prices_schema(db):
    with db.connect() as conn:
        cur = conn.cursor()
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
        conn.commit()
