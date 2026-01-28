from datetime import datetime
from typing import List

from Common.time import now_iso
from Statuses.settings_app.settings_statuses import INTERNAL_FINAL_STATUSES


def get_active_postings(db) -> List[dict]:
    """
    Постинги, статусы которых нужно синхронизировать с OZON
    """
    final_statuses = list(INTERNAL_FINAL_STATUSES)
    if not final_statuses:
        final_statuses = [""]  # чтобы избежать ошибки IN ()

    query = f"""
        SELECT
            id,
            posting_number,
            status
        FROM confirmations
        WHERE status NOT IN ({','.join('?' for _ in final_statuses)})
    """

    with db.connect() as conn:
        cur = conn.cursor()
        cur.execute(query, final_statuses)
        rows = cur.fetchall()

    return [dict(row) for row in rows]


def update_internal_status(
    db,
    confirmation_id: int,
    new_status: str,
    error_message: str | None = None
):

    with db.connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE confirmations
            SET
                status = ?,
                error_message = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            new_status,
            error_message,
            now_iso(),
            confirmation_id
        ))


def set_check_error(db, confirmation_id: int, message: str):
    with db.connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE confirmations
            SET
                error_message = ?,
                updated_at = ?
            WHERE id = ?
        """, (message, now_iso(), confirmation_id))


