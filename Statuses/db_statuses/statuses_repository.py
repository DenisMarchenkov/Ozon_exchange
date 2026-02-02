from typing import List

from Common.time import now_iso
from Statuses.settings_app.settings_statuses import OZON_FINAL_STATUSES


def get_active_postings(db, division_id: str) -> List[dict]:
    """
    Постинги, статусы которых нужно синхронизировать с OZON.
    Проверяем только те, у которых статус Ozon еще не финальный.
    """
    final_ozon = list(OZON_FINAL_STATUSES)
    if not final_ozon:
        final_ozon = [""]  # чтобы NOT IN () не сломался

    placeholders = ",".join("?" for _ in final_ozon)

    query = f"""
        SELECT
            id,
            posting_number,
            status,
            marketplace_status
        FROM confirmations
        WHERE (
                marketplace_status IS NULL
                OR marketplace_status NOT IN ({placeholders})
              )
          AND division_id = ?
    """

    params = [*final_ozon, division_id]

    with db.connect() as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()

    return [dict(row) for row in rows]


def update_ozon_info(
    db,
    confirmation_id: int,
    marketplace_status: str,
    marketplace_cancel_reason: str | None = None,
    error_message: str | None = None,
):

    with db.connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE confirmations
            SET
                marketplace_status = :marketplace_status,
                marketplace_cancel_reason = :marketplace_cancel_reason,
                marketplace_status_updated_at = :marketplace_status_updated_at,
                error_message = :error_message,
                updated_at = :now_iso
            WHERE posting_number = :conf_id
        """, {
            "marketplace_status": marketplace_status,
            "marketplace_cancel_reason": marketplace_cancel_reason,
            "marketplace_status_updated_at": now_iso(),
            "error_message": error_message,
            "now_iso": now_iso(),
            "conf_id": confirmation_id
        })
        conn.commit()


def set_check_error(db, confirmation_id: int, message: str):
    with db.connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE confirmations
            SET
                error_message = :message,
                updated_at = :now_iso
            WHERE posting_number = :conf_id
        """, {
            "message": message,
            "now_iso": now_iso(),
            "conf_id": confirmation_id
        })
        conn.commit()


