import requests
from typing import List, Optional

from Common.http_utils import send_request_with_retries
from Common.logger import get_logger
from Common.settings import YANDEX_API_TOKEN, YANDEX_BUSINESS_ID

logger = get_logger(__name__)


class YandexLabelsAPI:
    """
    Работа с API Yandex Market для генерации и получения отчета с наклейками.
    Только HTTP, без ожиданий и бизнес-логики.
    """

    GENERATE_URL = "https://api.partner.market.yandex.ru/reports/documents/labels/generate"
    STATUS_URL = "https://api.partner.market.yandex.ru/reports/info/{report_id}"

    def __init__(self, format_pdf: str = "A7"):
        self.business_id = int(YANDEX_BUSINESS_ID) if str(YANDEX_BUSINESS_ID).isdigit() else YANDEX_BUSINESS_ID
        # self.headers = {
        #     "Authorization": f"Bearer {YANDEX_API_TOKEN}",
        #     "Content-Type": "application/json",
        # }
        self.headers = {
            "Api-Key": YANDEX_API_TOKEN,
            'Accept': 'application/json',
            'X-Market-Integration': 'OrderGuard_NEW'
        }
        self.format_pdf = format_pdf

    # -------------------------------------------------
    # Создание отчета (задачи)
    # -------------------------------------------------
    def create_report(self, order_ids: List[str]) -> str | None:
        int_order_ids = []
        for oid in order_ids:
            try:
                int_order_ids.append(int(oid))
            except ValueError:
                logger.error(f"Невозможно преобразовать order_id в int: {oid}")
                continue
                
        if not int_order_ids:
            return None

        payload = {
            "businessId": self.business_id,
            "orderIds": int_order_ids,
            "sortingType": "SORT_BY_GIVEN_ORDER",
        }

        response = send_request_with_retries(
            url=f"{self.GENERATE_URL}?format={self.format_pdf}",
            method="POST",
            headers=self.headers,
            body=payload,
            accepted_status_codes=[200, 201],
        )

        if not response:
            logger.error("Yandex не вернул response при создании отчета наклеек")
            return None

        if not isinstance(response, dict):
             logger.error(f"Неожиданный формат ответа Yandex (ожидался dict, получено {type(response)}): {response}")
             return None

        report_id = response.get("result", {}).get("reportId")
        if not report_id:
             logger.error(f"reportId отсутствует в ответе Yandex: {response}")
             return None

        logger.info(f"Создан отчет наклеек Yandex: report_id={report_id}")
        return report_id

    # -------------------------------------------------
    # Проверка статуса отчета
    # -------------------------------------------------
    def get_report_status(self, report_id: str) -> dict:
        url = self.STATUS_URL.format(report_id=report_id)

        response = send_request_with_retries(
            url=url,
            method="GET",
            headers=self.headers,
        )

        if not response:
            return {"status": "error"}

        result = response.get("result", {})
        
        # Если статус не пришел в ответе (например, ошибка формата), ставим error
        if not result.get("status"):
            result["status"] = "error"
            
        return result
