import datetime
import os
import sys
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ===== ИМПОРТЫ ИЗ НОВОЙ СТРУКТУРЫ =====

from Orders.utils.safe_cast import safe_str, safe_int, safe_float
from Orders.utils.validators import validate_product_record
from Orders.utils.date_utils import parse_iso_date
from Orders.dbf_tools.dbf_writer import save_to_dbf
from Orders.services.order_processor import save_to_files_server_response


# =========================
# TEST SAFE_* HELPERS
# =========================

def test_safe_str():
    assert safe_str("hello", 10) == "hello"
    assert safe_str("hello world", 5) == "hello"
    assert safe_str(None, 10) == ""


def test_safe_int():
    assert safe_int("10") == 10
    assert safe_int(5) == 5
    assert safe_int("abc") is None


def test_safe_float():
    assert safe_float("10.5") == 10.5
    assert safe_float(3) == 3.0
    assert safe_float("abc") is None


# =========================
# TEST VALIDATE PRODUCT
# =========================

def test_validate_product_ok():
    product = {
        "offer_id": "SKU123",
        "name": "Товар",
        "price": "100.50",
        "quantity": 2,
    }

    ok, msg = validate_product_record(product)

    assert ok is True
    assert msg == ""


@pytest.mark.parametrize("product", [
    {"name": "Товар", "price": 10, "quantity": 1},        # нет offer_id
    {"offer_id": "1", "price": 10, "quantity": 1},       # нет name
    {"offer_id": "1", "name": "x", "price": 0, "quantity": 1},  # price 0
    {"offer_id": "1", "name": "x", "price": "abc", "quantity": 1},  # price не число
    {"offer_id": "1", "name": "x", "price": 10, "quantity": 0},  # qty 0
])
def test_validate_product_fail(product):
    ok, msg = validate_product_record(product)
    assert ok is False
    assert isinstance(msg, str)


# =========================
# TEST PARSE ISO DATE
# =========================

def test_parse_iso_date_ok():
    d = parse_iso_date("2025-12-04T10:00:00Z")
    assert d == datetime.date(2025, 12, 4)


def test_parse_iso_date_none():
    assert parse_iso_date(None) is None


def test_parse_iso_date_invalid():
    assert parse_iso_date("xxx") is None


# =========================
# TEST SAVE_TO_DBF
# =========================

def make_valid_products():
    return [
        {"offer_id": "SKU1", "name": "Товар 1", "price": "100", "quantity": 2},
        {"offer_id": "SKU2", "name": "Товар 2", "price": 200, "quantity": 1},
    ]


@patch("Orders.dbf_tools.dbf_writer.dbf.Table")
def test_save_to_dbf_ok(mock_table):
    mock_table_instance = MagicMock()
    mock_table.return_value = mock_table_instance

    products = make_valid_products()

    save_to_dbf(
        filename="test.dbf",
        products=products,
        posting_number="POST1",
        order_date_iso="2025-12-01T10:00:00Z",
        shipment_date_iso="2025-12-02T10:00:00Z",
        comment_for_supplier="Test",
        customer_id_in_supplier_crm="1",
        division_id="2",
    )

    assert mock_table_instance.open.called
    assert mock_table_instance.append.call_count == 2
    assert mock_table_instance.close.called


@patch("Orders.dbf_tools.dbf_writer.dbf.Table")
def test_save_to_dbf_empty_products(mock_table):
    save_to_dbf(
        filename="test.dbf",
        products=[],
        posting_number="POST1",
        order_date_iso=None,
        shipment_date_iso=None,
        comment_for_supplier="Test",
        customer_id_in_supplier_crm="1",
        division_id="2",
    )

    assert not mock_table.called


@patch("Orders.dbf_tools.dbf_writer.dbf.Table")
def test_save_to_dbf_invalid_product(mock_table):
    products = [
        {"offer_id": "SKU1", "name": "Товар 1", "price": "0", "quantity": 2}
    ]

    save_to_dbf(
        filename="test.dbf",
        products=products,
        posting_number="POST1",
        order_date_iso=None,
        shipment_date_iso=None,
        comment_for_supplier="Test",
        customer_id_in_supplier_crm="1",
        division_id="2",
    )

    assert not mock_table.called


# =========================
# TEST SAVE_TO_FILES_SERVER_RESPONSE
# =========================

@patch("Orders.services.order_processor.save_to_dbf")
@patch("Orders.services.order_processor.os.path.exists", return_value=False)
@patch("Orders.services.order_processor.os.makedirs")
def test_save_to_files_server_response_ok(mock_mkdir, mock_exists, mock_save):
    resp = {
        "result": {
            "postings": [
                {
                    "posting_number": "POST1",
                    "in_process_at": "2025-12-01T10:00:00Z",
                    "shipment_date": "2025-12-02T10:00:00Z",
                    "products": make_valid_products(),
                    "requirements": {},
                }
            ]
        }
    }

    save_to_files_server_response(resp)

    assert mock_save.called


@patch("Orders.services.order_processor.save_to_dbf")
@patch("Orders.services.order_processor.os.path.exists", return_value=True)
@patch("Orders.services.order_processor.os.makedirs")
def test_save_to_files_server_response_file_exists(mock_mkdir, mock_exists, mock_save):
    resp = {
        "result": {
            "postings": [
                {
                    "posting_number": "POST1",
                    "products": make_valid_products(),
                }
            ]
        }
    }

    save_to_files_server_response(resp)

    assert not mock_save.called
