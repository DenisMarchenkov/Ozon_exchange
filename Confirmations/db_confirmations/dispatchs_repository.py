import sqlite3
from pathlib import Path
from typing import List, Dict
from Common.settings import DB_PATH


class DispatchRepository:
    """
    Репозиторий dispatch-событий и связанных файлов.
    Поддерживает:
    - несколько posting_number на один dispatch
    - хранение файлов (наклейки, файл склада)
    """

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    # ------------------------------
    # DB connection
    # ------------------------------
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON;")
        cur.execute("PRAGMA journal_mode = WAL;")
        cur.execute("PRAGMA synchronous = NORMAL;")
        return conn

    # ------------------------------
    # Init DB
    # ------------------------------
    def _init_db(self):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS dispatch (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS dispatch_postings (
                    dispatch_id TEXT NOT NULL,
                    posting_number TEXT NOT NULL,
                    FOREIGN KEY(dispatch_id) REFERENCES dispatch(id) ON DELETE CASCADE,
                    FOREIGN KEY(posting_number) REFERENCES confirmations(posting_number) ON DELETE CASCADE,
                    UNIQUE(dispatch_id, posting_number)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS dispatch_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dispatch_id TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(dispatch_id) REFERENCES dispatch(id) ON DELETE CASCADE
                )
            """)
            conn.commit()

    # ------------------------------
    # Dispatch CRUD
    # ------------------------------
    def create_dispatch(self, dispatch_id: str, created_at: str, status: str = "CREATED"):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO dispatch (id, status, created_at)
                VALUES (?, ?, ?)
            """, (dispatch_id, status, created_at))
            conn.commit()

    def add_postings(self, dispatch_id: str, postings: List[str]):
        if not postings:
            return
        placeholders = ",".join("(?,?)" for _ in postings)
        values = []
        for posting in postings:
            values.append(dispatch_id)
            values.append(posting)
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(f"""
                INSERT OR IGNORE INTO dispatch_postings (dispatch_id, posting_number)
                VALUES {placeholders}
            """, values)
            conn.commit()

    def get_postings(self, dispatch_id: str) -> List[str]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT posting_number
                FROM dispatch_postings
                WHERE dispatch_id = ?
            """, (dispatch_id,))
            return [row["posting_number"] for row in cur.fetchall()]

    def update_status(self, dispatch_id: str, status: str):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE dispatch
                SET status = ?
                WHERE id = ?
            """, (status, dispatch_id))
            conn.commit()

    def get_status(self, dispatch_id: str) -> str | None:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT status FROM dispatch WHERE id=?", (dispatch_id,))
            row = cur.fetchone()
            return row["status"] if row else None

    def exists(self, dispatch_id: str) -> bool:
        return self.get_status(dispatch_id) is not None

    def get_dispatch(self, dispatch_id: str) -> dict | None:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM dispatch WHERE id=?", (dispatch_id,))
            row = cur.fetchone()
            if not row:
                return None
            dispatch = dict(row)
            dispatch["postings"] = self.get_postings(dispatch_id)
            return dispatch

    def get_all_dispatch(self) -> List[dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM dispatch ORDER BY created_at DESC")
            rows = [dict(row) for row in cur.fetchall()]
            for row in rows:
                row["postings"] = self.get_postings(row["id"])
            return rows

    # ------------------------------
    # Files
    # ------------------------------
    def add_file(self, dispatch_id: str, file_type: str, file_path: Path):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO dispatch_files (dispatch_id, file_type, file_path)
                VALUES (?, ?, ?)
            """, (dispatch_id, file_type, str(file_path)))
            conn.commit()

    def get_files(self, dispatch_id: str) -> List[Dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM dispatch_files
                WHERE dispatch_id = ?
                ORDER BY id
            """, (dispatch_id,))
            return [dict(row) for row in cur.fetchall()]

    def get_all_files(self) -> List[Dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM dispatch_files ORDER BY id")
            return [dict(row) for row in cur.fetchall()]

    def is_sent(self, dispatch_id: str) -> bool:
        return self.get_status(dispatch_id) == "SENT"

