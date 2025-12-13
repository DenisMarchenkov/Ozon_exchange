from Common.logger import get_logger
from Confirmations.api.ozon_confirmations_api import OzonConfirmationsAPI
from Confirmations.db_confirmations.confirmations_repository import ConfirmationsRepository
from Confirmations.utils.time import now_iso

logger = get_logger("ConfirmationsDeliveryService")


class ConfirmationsStatusUpdater:
    """
    Получает список posting_numbers → обновляет статусы на Ozon →
    обновляет статус в локальной БД (confirmations).
    """

    def __init__(self):
        self.api = OzonConfirmationsAPI()
        self.repo = ConfirmationsRepository()

    def process_deliveries(self, posting_numbers: list[str]):
        logger.info(f"Начинаем обновление {len(posting_numbers)} заказов")

        for pn in posting_numbers:

            try:
                ok, err = self.api.ship_posting(pn)
            except Exception as e:
                ok = False
                err = f"{e}"
                logger.exception(f"{pn}: Внутренняя ошибка обработки")
            # ok = False # для тестов
            if ok:
                self.repo.update_status(pn, "awaiting_delivery", now_iso())
                logger.info(f"{pn}: статус обновлён в БД")
            else:
                self.repo.update_status(pn, "error", now_iso(), err,)
                logger.error(f"{pn}: ошибка ship — {err}")

        logger.info("Обновление статусов завершено")