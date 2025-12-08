import os
import pytest

from Common.db import get_connection
from Orders.services.db_orders import (
    init_db,
    create_order,
    get_order_status,
    update_order_status
)

TEST_DB_PATH = "test_orders.db"


@pytest.fixture(autouse=True)
def clear_test_db(monkeypatch):
    """Перед каждым тестом создаём чистую тестовую базу."""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    # подменяем путь к БД
    monkeypatch.setattr("Common.db.DB_PATH", TEST_DB_PATH)

    init_db()
    yield

    # после теста удаляем
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


def test_init_db_creates_table():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='orders';"
        )
        assert cursor.fetchone() is not None


def test_create_order_inserts_row():
    create_order("TEST-001", "new")
    status = get_order_status("TEST-001")
    assert status == "new"


def test_get_order_status_returns_none_for_unknown():
    status = get_order_status("UNKNOWN")
    assert status is None


def test_update_order_status_changes_status():
    create_order("TEST-002", "new")
    update_order_status("TEST-002", "dbf_created")
    status = get_order_status("TEST-002")
    assert status == "dbf_created"


def test_create_order_does_not_duplicate():
    create_order("TEST-003", "new")
    create_order("TEST-003", "ignored_new")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM orders WHERE posting_number = 'TEST-003'")
        count = cursor.fetchone()[0]

    assert count == 1
    assert get_order_status("TEST-003") == "new"
