import asyncio
import aiohttp
from Common.logger import get_logger
from Statuses.db_statuses.statuses_repository import get_active_postings, update_ozon_info, set_check_error
from Statuses.api.ozon_client import OzonClient
from Statuses.services.mailers.status_mailer import StatusMailer
from Statuses.settings_app.settings_statuses import OZON_DIVISION

logger = get_logger(__name__)


class StatusChecker:
    def __init__(self, db, ozon_headers, max_concurrent_requests=5):
        self.db = db
        self.ozon_client = OzonClient(
            headers=ozon_headers,
            max_concurrent_requests=max_concurrent_requests
        )
        self.status_changes = []

    async def run(self):
        # 1️⃣ Берём все активные постинги
        active_postings = get_active_postings(self.db, division_id=OZON_DIVISION)
        if not active_postings:
            logger.info("Нет активных подтверждений для проверки.")
            return

        async with aiohttp.ClientSession() as session:
            # 2️⃣ Создаём задачи для каждого постинга
            tasks = [
                self._process_single_posting(session, p)
                for p in active_postings
            ]
            
            # 3️⃣ Запускаем всё параллельно
            await asyncio.gather(*tasks)

        # 4️⃣ Отправляем уведомление, если были изменения
        if self.status_changes:
            logger.info("Отправка уведомления об изменении статусов (%s изменений)...", len(self.status_changes))
            mailer = StatusMailer(self.status_changes)
            await asyncio.to_thread(mailer.send)
        else:
            logger.info("Изменений статусов не обнаружено, уведомление не требуется.")

        logger.info("Проверка завершена. Обработано заказов: %s. Найдено изменений: %s.", len(active_postings), len(self.status_changes))

    async def _process_single_posting(self, session: aiohttp.ClientSession, posting: dict):
        posting_number = posting["posting_number"]
        conf_id = posting["id"]
        old_marketplace_status = posting.get("marketplace_status")
        internal_status = posting.get("status")

        # Получаем данные от Ozon (внутри семафор OzonClient)
        res = await self.ozon_client.get_posting_status(session, posting_number)
        
        new_marketplace_status = res.get("status")
        cancel_reason = res.get("cancel_reason")
        error = res.get("error")

        if error:
            # Используем to_thread для синхронных вызовов БД, чтобы не блокировать цикл
            await asyncio.to_thread(set_check_error, self.db, conf_id, error)
            logger.warning("[%s] Ошибка запроса: %s", posting_number, error)
            return

        # Обновляем инфо в БД сразу по готовности ответа
        await asyncio.to_thread(
            update_ozon_info,
            self.db,
            conf_id,
            marketplace_status=new_marketplace_status,
            marketplace_cancel_reason=cancel_reason
        )

        # Определяем новый внутренний статус на основе логики в БД
        new_internal_status = "cancelled" if new_marketplace_status == "cancelled" else internal_status

        if new_marketplace_status != old_marketplace_status:
            self.status_changes.append({
                "posting_number": posting_number,
                "old_status": old_marketplace_status,
                "new_status": new_marketplace_status,
                "old_internal_status": internal_status,
                "new_internal_status": new_internal_status,
            })
            logger.info("[%s] Обнаружено изменение статуса: %s -> %s", posting_number, old_marketplace_status, new_marketplace_status)
        else:
            logger.info("[%s] Статус не изменился (%s)", posting_number, new_marketplace_status)
