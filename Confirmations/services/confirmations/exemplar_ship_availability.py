from typing import Dict, List

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

    def divide_postings(self, ozon_confirmations: list[dict]) -> Dict[str, List[str]]:
        """
        Делит список заказов на группы по статусу.
        """
        result = {
            "ship_available": [],
            "ship_not_available": [],
            "validation_in_process": [],
            "update_available": [],
            "update_not_available": [],
            "unknown": [],
        }

        for c in ozon_confirmations:
            posting_number = c["posting_number"]

            try:
                resp = self.get_full_status(posting_number)
                status = resp.get("status")
            except Exception as e:
                logger.error(f"[EX_STATUS] {posting_number}: ошибка получения статуса: {e}")
                status = "unknown"

            if status == self.STATUS_SHIP_AVAILABLE:
                result["ship_available"].append(posting_number)
            elif status == self.STATUS_SHIP_NOT_AVAILABLE:
                result["ship_not_available"].append(posting_number)
            elif status == self.STATUS_VALIDATION:
                result["validation_in_process"].append(posting_number)
            elif status == self.STATUS_UPDATE_AVAILABLE:
                result["update_available"].append(posting_number)
            elif status == self.STATUS_UPDATE_NOT_AVAILABLE:
                result["update_not_available"].append(posting_number)
            else:
                result["unknown"].append(posting_number)

        return result
