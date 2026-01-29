import pytest
import sqlite3
import os
import sys
from unittest.mock import patch

# Mocking DB_PATH before import to avoid errors
with patch("Common.settings.DB_PATH", "fake.db"):
    from Statuses.scripts.migrate_ozon_status import migrate

def test_migration_adds_columns(tmp_path):
    # Create a dummy DB without the columns
    db_file = tmp_path / "test_migration.db"
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE confirmations (
            id INTEGER PRIMARY KEY,
            posting_number TEXT,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

    # Run migration with mocked DB_PATH
    with patch("Statuses.scripts.migrate_ozon_status.DB_PATH", str(db_file)):
        migrate()

    # Verify columns exist
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(confirmations)")
    cols = [row[1] for row in cur.fetchall()]
    conn.close()

    assert "ozon_status" in cols
    assert "ozon_status_updated_at" in cols
    assert "ozon_cancel_reason" in cols

def test_migration_idempotent(tmp_path):
    db_file = tmp_path / "test_idempotent.db"
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("CREATE TABLE confirmations (id INTEGER)")
    conn.commit()
    conn.close()

    with patch("Statuses.scripts.migrate_ozon_status.DB_PATH", str(db_file)):
        migrate()
        # Second run should not fail
        migrate()

    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(confirmations)")
    cols = [row[1] for row in cur.fetchall()]
    conn.close()
    
    # Check that they haven't been added twice (SQLite adds them once, but script should handle)
    assert cols.count("ozon_status") == 1
