import requests
from typing import List

from Common.http_utils import send_request_with_retries
from Common.logger import get_logger
from Common.settings import YANDEX_API_TOKEN, YANDEX_CAMPAIGN_ID

logger = get_logger(__name__)

class YandexConfirmationsAPI:
    """
    Работа с API Yandex Market для изменения статусов заказов.
    """

    STATUS_UPDATE_URL = "https://api.partner.market.yandex.ru/campaigns/{campaign_id}/orders/status-update"

    def __init__(self):
        self.campaign_id = YANDEX_CAMPAIGN_ID
        self.headers = {
            "Api-Key": YANDEX_API_TOKEN,
            'Accept': 'application/json',
            'X-Market-Integration': 'OrderGuard_NEW'
        }

    def update_order_statuses(self, order_ids: List[str], new_status: str, new_substatus: str) -> bool:
        """
        Обновляет статусы заказов.
        Возвращает True, если запрос был успешным.
        """
        if not order_ids:
            return True

        url = self.STATUS_UPDATE_URL.format(campaign_id=self.campaign_id)
        
        orders_payload = []
        for order_id in order_ids:
            try:
                orders_payload.append({
                    "id": int(order_id),
                    "status": new_status,
                    "substatus": new_substatus
                })
            except ValueError:
                logger.error(f"Невозможно преобразовать order_id в int: {order_id}")
                continue
                
        if not orders_payload:
            return False

        payload = {"orders": orders_payload}

        logger.info(f"Отправка {len(orders_payload)} заказов на обновление статусов в Yandex...")
        
        # Используем существующий механизм send_request_with_retries
        response = send_request_with_retries(
            url=url,
            method="POST",
            headers=self.headers,
            body=payload,
            accepted_status_codes=[200],
        )

        # Если ответ не пустой и запрос прошел (send_request_with_retries вернет dict),
        # считаем статусы успешно обновленными.
        if response is not None:
            logger.info("Статусы заказов успешно обновлены в Yandex.")
            return True
        else:
            logger.error("Ошибка при обновлении статусов заказов в Yandex.")
            return False
