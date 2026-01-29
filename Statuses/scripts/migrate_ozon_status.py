import sqlite3
import os
import sys

# Добавляем корень проекта в путь поиска модулей
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

# Теперь можно импортировать из Common
from Common.settings import DB_PATH

def migrate():
    #load_dotenv()
    db_path = DB_PATH
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    print(f"Migrating database: {db_path}")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Поля для добавления
    columns_to_add = [
        ("marketplace_status", "TEXT"),
        ("marketplace_status_updated_at", "TEXT"),
        ("marketplace_cancel_reason", "TEXT")
    ]

    # Проверяем существующие колонки
    cur.execute("PRAGMA table_info(confirmations)")
    existing_columns = [row[1] for row in cur.fetchall()]

    for col_name, col_type in columns_to_add:
        if col_name not in existing_columns:
            print(f"Adding column {col_name}...")
            cur.execute(f"ALTER TABLE confirmations ADD COLUMN {col_name} {col_type}")
        else:
            print(f"Column {col_name} already exists.")

    conn.commit()
    conn.close()
    print("Migration finished.")

if __name__ == "__main__":
    migrate()
