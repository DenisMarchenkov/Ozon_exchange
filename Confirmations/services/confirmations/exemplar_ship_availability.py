from typing import Dict, List, Any
from Common.logger import get_logger
from Confirmations.api.ozon_exemplar_status_api import OzonExemplarStatusAPI

logger = get_logger(__name__)


class ExemplarShipAvailabilityService:
    """
    Сервис проверки статусов экземпляров Ozon.
    Делит отправления на группы по статусу.
    """

    STATUS_SHIP_AVAILABLE = "ship_available"
    STATUS_SHIP_NOT_AVAILABLE = "ship_not_available"
    STATUS_VALIDATION = "validation_in_process"
    STATUS_UPDATE_AVAILABLE = "update_available"
    STATUS_UPDATE_NOT_AVAILABLE = "update_not_available"

    def __init__(self):
        self.api = OzonExemplarStatusAPI()

    def can_ship(self, posting_number: str) -> bool:
        """
        True если можно собирать (ship_available)
        """
        try:
            resp = self.api.get_status(posting_number)
        except Exception as e:
            logger.error(f"[EX_STATUS] {posting_number}: ошибка API: {e}")
            return False

        status = resp.get("status")

        logger.info(f"[EX_STATUS] {posting_number}: статус экземпляров = {status}")

        return status == self.STATUS_SHIP_AVAILABLE

    def get_full_status(self, posting_number: str) -> dict:
        """
        Возвращает полный сырой ответ Ozon
        """
        return self.api.get_status(posting_number)

    def divide_postings(self, ozon_confirmations: list[dict]) -> dict[str, dict[str, dict]]:
        """
        Делит список заказов на группы по статусу.
        Возвращает словарь вида:
        {
            "ship_available": {posting_number: resp},
            "ship_not_available": {posting_number: resp},
            ...
        }
        """
        # словарь для группировки
        result = {
            "ship_available": {},
            "ship_not_available": {},
            "validation_in_process": {},
            "update_available": {},
            "update_not_available": {},
            "unknown": {},
        }

        # соответствие статусов Ozon → ключи result
        status_map = {
            self.STATUS_SHIP_AVAILABLE: "ship_available",
            self.STATUS_SHIP_NOT_AVAILABLE: "ship_not_available",
            self.STATUS_VALIDATION: "validation_in_process",
            self.STATUS_UPDATE_AVAILABLE: "update_available",
            self.STATUS_UPDATE_NOT_AVAILABLE: "update_not_available",
        }

        for c in ozon_confirmations:
            posting_number = c["posting_number"]

            try:
                resp = self.get_full_status(posting_number)
                status = resp.get("status")
            except Exception as e:
                logger.error(f"[EX_STATUS] {posting_number}: ошибка получения статуса: {e}")
                status = "unknown"
                resp = {}  # если ошибка, значение тоже словарь

            key = status_map.get(status, "unknown")
            result[key][posting_number] = resp

        return result

