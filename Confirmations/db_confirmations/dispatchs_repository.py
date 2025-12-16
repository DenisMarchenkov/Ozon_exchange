import sqlite3
from pathlib import Path
from Common.settings import DB_PATH


class DispatchRepository:
    """
    Репозиторий для работы с dispatch и dispatch_files
    """

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    # ------------------------------
    # Подключение к БД
    # ------------------------------
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON;")
        cur.execute("PRAGMA synchronous = NORMAL;")
        return conn

    # ------------------------------
    # Инициализация таблиц
    # ------------------------------
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA journal_mode = WAL;")

            cur.execute("""
                CREATE TABLE IF NOT EXISTS dispatch (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS dispatch_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dispatch_id TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(dispatch_id)
                        REFERENCES dispatch(id)
                        ON DELETE CASCADE
                )
            """)

    # ------------------------------
    # CRUD: Dispatch
    # ------------------------------
    def create_dispatch(self, dispatch_id: str, created_at: str):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO dispatch (id, status, created_at) VALUES (?, ?, ?)",
                (dispatch_id, "CREATED", created_at)
            )

    def update_status_dispatch(self, dispatch_id: str, status: str):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE dispatch SET status=? WHERE id=?",
                (status, dispatch_id)
            )

    def get_all_dispatch(self) -> list[dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM dispatch"
            )
            return [dict(row) for row in cur.fetchall()]

    def exists(self, dispatch_id: str) -> bool:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM dispatch WHERE id=?",
                (dispatch_id,)
            )
            return cur.fetchone() is not None

    # ------------------------------
    # CRUD: Dispatch Files
    # ------------------------------
    def add_file(self, dispatch_id: str, file_type: str, file_path: Path):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO dispatch_files (dispatch_id, file_type, file_path)
                VALUES (?, ?, ?)
                """,
                (dispatch_id, file_type, str(file_path))
            )

    def get_files(self, dispatch_id: str) -> list[dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM dispatch_files WHERE dispatch_id=?",
                (dispatch_id,)
            )
            return [dict(row) for row in cur.fetchall()]

    def get_all_files(self) -> list[dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM dispatch_files"
            )
            return [dict(row) for row in cur.fetchall()]

    # ------------------------------
    # Удобный метод проверки отправки
    # ------------------------------
    def is_sent(self, dispatch_id: str) -> bool:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT status FROM dispatch WHERE id=?",
                (dispatch_id,)
            )
            row = cur.fetchone()
            return row is not None and row["status"] == "SENT"
