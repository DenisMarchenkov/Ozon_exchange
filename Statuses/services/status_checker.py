import logging
from Common.logger import get_logger
from Statuses.settings_app.settings_statuses import OZON_TO_INTERNAL_STATUS
from Statuses.db_statuses.statuses_repository import get_active_postings, update_internal_status, set_check_error
from Statuses.api.ozon_client import OzonClient

logger = get_logger(__name__)


class StatusChecker:
    def __init__(self, db, ozon_headers, max_concurrent_requests=5):
        self.db = db
        self.ozon_client = OzonClient(
            headers=ozon_headers,
            max_concurrent_requests=max_concurrent_requests
        )

    async def run(self):
        # 1️⃣ Берём все активные постинги
        active_postings = get_active_postings(self.db)
        if not active_postings:
            logger.info("Нет активных подтверждений для проверки.")
            return

        posting_numbers = [p["posting_number"] for p in active_postings]

        # 2️⃣ Получаем статусы с OZON
        results = await self.ozon_client.get_many(posting_numbers)

        # 3️⃣ Обрабатываем каждый результат
        for res in results:
            posting_number = res["posting_number"]
            status = res.get("status")
            cancel_reason = res.get("cancel_reason")
            error = res.get("error")

            # Находим id в нашей БД
            confirmation = next(
                (p for p in active_postings if p["posting_number"] == posting_number), None
            )
            if not confirmation:
                logger.warning("[%s] Не найдено в БД", posting_number)
                continue

            conf_id = confirmation["id"]

            # Ошибка запроса
            if error:
                set_check_error(self.db, conf_id, error)
                logger.warning("[%s] Ошибка запроса: %s", posting_number, error)
                continue

            # Маппим OZON → внутренний статус
            new_status = OZON_TO_INTERNAL_STATUS.get(status)
            if not new_status:
                logger.warning("[%s] Неизвестный статус OZON: %s", posting_number, status)
                set_check_error(self.db, conf_id, f"Неизвестный OZON статус: {status}")
                continue

            # Обновляем статус
            update_internal_status(self.db, conf_id, new_status)
            logger.info("[%s] Обновлён статус: %s", posting_number, new_status)
