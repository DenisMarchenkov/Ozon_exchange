import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone

from Common.settings import DB_PATH


class DispatchRepository:
    """
    Репозиторий агрегата Dispatch.

    Dispatch:
    - владеет статусом
    - владеет файлами
    - НЕ владеет postings (они живут в confirmations.dispatch_id)
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

    # ------------------------------
    # Helpers
    # ------------------------------
    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ------------------------------
    # Dispatch CRUD
    # ------------------------------
    def create_dispatch(self, dispatch_id: str, status: str = "NEW"):
        """
        Создаёт dispatch.
        """
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO dispatch (id, status, created_at)
                VALUES (?, ?, ?)
            """, (dispatch_id, status, self._now()))
            conn.commit()

    def exists(self, dispatch_id: str) -> bool:
        return self.get_status(dispatch_id) is not None

    def get_status(self, dispatch_id: str) -> Optional[str]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT status
                FROM dispatch
                WHERE id = ?
            """, (dispatch_id,))
            row = cur.fetchone()
            return row["status"] if row else None

    def update_status(self, dispatch_id: str, status: str):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE dispatch
                SET status = ?
                WHERE id = ?
            """, (status, dispatch_id))
            conn.commit()

    def get(self, dispatch_id: str) -> Optional[Dict]:
        """
        Возвращает агрегат dispatch.
        """
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT *
                FROM dispatch
                WHERE id = ?
            """, (dispatch_id,))
            row = cur.fetchone()
            if not row:
                return None

            dispatch: Dict[str, Any] = dict(row)
            dispatch["files"] = self.get_files(dispatch_id)
            return dispatch

    def get_dispatch_id_by_status(self, status: str) -> List[Dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT id
            FROM dispatch
            WHERE status = ?
            """, (status,))
            return [dict(row) for row in cur.fetchall()]


    # ------------------------------
    # Files
    # ------------------------------
    def has_file(self, dispatch_id: str, file_type: str) -> bool:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT 1
                FROM dispatch_files
                WHERE dispatch_id = ?
                  AND file_type = ?
                LIMIT 1
            """, (dispatch_id, file_type))
            return cur.fetchone() is not None

    def add_file(self, dispatch_id: str, file_type: str, file_path: Path):
        """
        Идемпотентно добавляет файл к dispatch.
        """
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT OR IGNORE INTO dispatch_files
                (dispatch_id, file_type, file_path, created_at)
                VALUES (?, ?, ?, ?)
            """, (dispatch_id, file_type, str(file_path), self._now()))
            conn.commit()

    def get_files(self, dispatch_id: str) -> List[Dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT *
                FROM dispatch_files
                WHERE dispatch_id = ?
                ORDER BY id
            """, (dispatch_id,))
            return [dict(row) for row in cur.fetchall()]


    def get_all_files(self):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT *
            FROM dispatch_files
            """)
            return [dict(row) for row in cur.fetchall()]

    def get_file_types(self, dispatch_id: str) -> list[str]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT file_type FROM dispatch_files WHERE dispatch_id=?",
                (dispatch_id,)
            )
            return [row["file_type"] for row in cur.fetchall()]


    def get_files_by_status_dispatch(self, status: str ) -> List[Dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT df.*
            FROM dispatch_files df
            JOIN dispatch d ON d.id = df.dispatch_id
            WHERE d.status = ?
            """, (status,))
            return [dict(row) for row in cur.fetchall()]


    # ------------------------------
    # Business helpers
    # ------------------------------
    def is_prepared(self, dispatch_id: str) -> bool:
        return self.get_status(dispatch_id) == "PREPARED"

    def is_sent(self, dispatch_id: str) -> bool:
        return self.get_status(dispatch_id) == "SENT"

    def get_all_dispatch(self) -> List[dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM dispatch ORDER BY created_at DESC")
            rows = [dict(row) for row in cur.fetchall()]

            return rows