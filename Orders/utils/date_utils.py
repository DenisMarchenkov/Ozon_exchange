import datetime

from typing import Optional
from Common.logger import get_logger
logger = get_logger("Orders")


def parse_iso_date(date_str: Optional[str]) -> Optional[datetime.date]:
    if not date_str:
        return None

    try:
        s = date_str.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(s)
        return dt.date()
    except Exception:
        logger.warning(f"Не удалось распарсить дату: {date_str}")
        return None