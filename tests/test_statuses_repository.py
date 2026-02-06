import pytest
import sqlite3
import os
from Common.db.database import Database
from Common.db.init_db import init_confirmations_schema
from Statuses.db_statuses.statuses_repository import get_active_postings, update_ozon_info, set_check_error
from Statuses.settings_app.settings_statuses import OZON_FINAL_STATUSES

@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_storage.db"
    db = Database(str(db_file))
    init_confirmations_schema(db)
    
    with db.connect() as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(confirmations)")
        rows = cur.fetchall()
        cols = [row["name"] for row in rows]
        
        # Гарантируем наличие колонок для теста
        if 'marketplace_status' not in cols:
            cur.execute("ALTER TABLE confirmations ADD COLUMN marketplace_status TEXT")
        if 'marketplace_status_updated_at' not in cols:
            cur.execute("ALTER TABLE confirmations ADD COLUMN marketplace_status_updated_at TEXT")
        if 'marketplace_cancel_reason' not in cols:
            cur.execute("ALTER TABLE confirmations ADD COLUMN marketplace_cancel_reason TEXT")
        conn.commit()
        
    return db

def test_get_active_postings(temp_db):
    with temp_db.connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO confirmations (posting_number, division_id, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, ('POST1', 1, 'new', '2026-01-28', '2026-01-28'))
        
        cur.execute("""
            INSERT INTO confirmations (posting_number, division_id, status, marketplace_status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('POST2', 1, 'new', 'awaiting_packaging', '2026-01-28', '2026-01-28'))
        
        cur.execute("""
            INSERT INTO confirmations (posting_number, division_id, status, marketplace_status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('POST3', 1, 'new', 'delivered', '2026-01-28', '2026-01-28'))
        conn.commit()

    active = get_active_postings(temp_db, division_id=1)
    posting_numbers = [p["posting_number"] for p in active]
    
    assert "POST1" in posting_numbers
    assert "POST2" in posting_numbers
    assert "POST3" not in posting_numbers

def test_update_ozon_info(temp_db):
    with temp_db.connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO confirmations (posting_number, division_id, status, created_at, updated_at)
            VALUES ('UPDATE_ME', 1, 'internal_status', '2026-01-28', '2026-01-28')
        """)
        conf_id = cur.lastrowid
        conn.commit()

    update_ozon_info(
        temp_db, 
        conf_id, 
        marketplace_status="delivering", 
        marketplace_cancel_reason="not cancelled",
        error_message="no error"
    )

    with temp_db.connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM confirmations WHERE id = ?", (conf_id,))
        row = cur.fetchone()

    assert row is not None
    assert row["status"] == "internal_status"
    assert row["marketplace_status"] == "delivering"
    assert row["marketplace_cancel_reason"] == "not cancelled"
    assert row["error_message"] == "no error"

    # Проверяем синхронизацию отмены
    update_ozon_info(
        temp_db,
        conf_id,
        marketplace_status="cancelled",
        marketplace_cancel_reason="customer cancelled"
    )

    with temp_db.connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT status, marketplace_status FROM confirmations WHERE id = ?", (conf_id,))
        row = cur.fetchone()

    assert row["marketplace_status"] == "cancelled"
    assert row["status"] == "cancelled"

def test_set_check_error(temp_db):
    with temp_db.connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO confirmations (posting_number, division_id, status, created_at, updated_at)
            VALUES ('ERROR_POST', 1, 'new', '2026-01-28', '2026-01-28')
        """)
        conf_id = cur.lastrowid
        conn.commit()

    set_check_error(temp_db, conf_id, "API Error 500")

    with temp_db.connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM confirmations WHERE id = ?", (conf_id,))
        row = cur.fetchone()

    assert row is not None
    assert row["error_message"] == "API Error 500"
