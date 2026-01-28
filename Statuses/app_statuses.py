import asyncio
from pprint import pprint

from Common.logger import get_logger
from Common.db.database import Database
from Common.settings import DB_PATH, API_TOKEN, CLIENT_ID
from Statuses.db_statuses.statuses_repository import get_active_postings
from Statuses.services.status_checker import StatusChecker
from Statuses.settings_app.settings_statuses import MAX_CONCURRENT_REQUESTS

logger = get_logger(__name__)

async def main():
    logger.info("=== Запуск проверки статусов ===")

    try:
        # 1️⃣ Инициализация БД
        db = Database(DB_PATH)

        # 2️⃣ Заголовки для Ozon API
        ozon_headers = {
            "Client-Id": CLIENT_ID,
            "Api-Key": API_TOKEN,
            "Content-Type": "application/json"
        }

        # 3️⃣ Инициализация StatusChecker
        checker = StatusChecker(
            db=db,
            ozon_headers=ozon_headers,
            max_concurrent_requests=MAX_CONCURRENT_REQUESTS
        )

        # 4️⃣ Асинхронный запуск
        await checker.run()

    except Exception as e:
        logger.exception("Фатальная ошибка при проверке статусов: %s", e)

    logger.info("=== Завершение проверки статусов ===")


if __name__ == "__main__":
    asyncio.run(main())

