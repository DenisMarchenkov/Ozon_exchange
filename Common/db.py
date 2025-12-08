import sqlite3

from contextlib import contextmanager
from Common.settings import DB_PATH


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()