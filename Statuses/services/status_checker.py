import asyncio
import aiohttp
from Common.logger import get_logger
from Common.settings import RECIPIENT_STOCK, RECIPIENT_MANAGERS
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
        self.discrepancies = []

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

        # 4️⃣ Отправляем уведомление, если были изменения или найдены рассинхроны
        if self.status_changes or self.discrepancies:
            from Common.settings import RECIPIENT_ADMIN
            
            logger.info("Отправка уведомления об изменении статусов (изменений: %s, рассинхронов: %s)...", 
                        len(self.status_changes), len(self.discrepancies))

            has_cancelled = any(c["new_status"] == "cancelled" for c in self.status_changes)
            
            # Логика получателей:
            # Если есть рассинхрон -> только админу
            if self.discrepancies:
                recipients = RECIPIENT_ADMIN
            else:
                # Если только обычные изменения -> менеджерам (+ склад при отменах)
                recipients = RECIPIENT_MANAGERS
                if has_cancelled:
                    recipients = RECIPIENT_MANAGERS + RECIPIENT_STOCK

            mailer = StatusMailer(self.status_changes, discrepancies=self.discrepancies, to=recipients)
            await asyncio.to_thread(mailer.send)
        else:
            logger.info("Изменений статусов не обнаружено, уведомление не требуется.")

        logger.info("Проверка завершена. Обработано заказов: %s. Найдено изменений: %s. Рассинхронов: %s.", 
                    len(active_postings), len(self.status_changes), len(self.discrepancies))

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

        # ДЕТЕКЦИЯ РАССИНХРОНА:
        # Если на Озоне заказ уже уехал (awaiting_deliver и далее), 
        # а у нас он все еще в начале пути (NEW, confirmed, error и т.д.)
        early_statuses = ['NEW', 'confirmed', 'awaiting_confirmation', 'ship_not_available', 'is_gtd_absent', 'is_marking_absent', 'error']
        advanced_ozon = ['awaiting_deliver', 'delivering', 'driver_pickup', 'delivered']
        
        if internal_status in early_statuses and new_marketplace_status in advanced_ozon:
            self.discrepancies.append({
                "posting_number": posting_number,
                "internal_status": internal_status,
                "marketplace_status": new_marketplace_status
            })
            logger.warning("[%s] ОБНАРУЖЕН РАССИНХРОН: внутр=%s, озон=%s", posting_number, internal_status, new_marketplace_status)

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
