from Common.http_utils import send_request_with_retries
from Common.settings import CLIENT_ID, API_TOKEN
from Common.logger import get_logger

logger = get_logger("ConfirmationsAPI")


class OzonConfirmationsAPI:
    """
    Клиент Ozon API для перевода заказов (posting_number)
    в статус awaiting_delivery.
    """

    URL_GET = "https://api-seller.ozon.ru/v3/posting/fbs/get"
    URL_SHIP = "https://api-seller.ozon.ru/v4/posting/fbs/ship"

    def __init__(self):
        self.headers = {
            "Client-Id": CLIENT_ID,
            "Api-Key": API_TOKEN,
            "Content-Type": "application/json"
        }

    # -----------------------------
    # Получение полной структуры заказа
    # -----------------------------
    def get_posting_info(self, posting_number: str):
        body = {
            "posting_number": posting_number,
            "with": {
                "analytics_data": False,
                "barcodes": False,
                "financial_data": False,
                "product_exemplars": False,
                "translit": False,
            }
        }

        logger.info(f"Получение данных заказа {posting_number}")

        response = send_request_with_retries(
            url=self.URL_GET,
            method="POST",
            headers=self.headers,
            body=body,
        )
        return response

    # -----------------------------
    # Преобразование данных заказа
    # в формат ship-запроса
    # -----------------------------
    @staticmethod
    def make_ship_payload(order_json: dict) -> dict:
        """
        order_json — это ответ от v3/posting/fbs/get
        Возвращаем структуру:
        {
           "posting_number": "...",
           "packages": [
              {"products": [{"sku":..., "quantity":...}, ...]}
           ]
        }
        """

        posting_number = order_json["result"]["posting_number"]

        products = []
        for item in order_json["result"]["products"]:
            products.append({
                "sku": item["sku"],
                "quantity": item["quantity"]
            })

        return {
            "posting_number": posting_number,
            "packages": [
                {"products": products}
            ]
        }

    # -----------------------------
    # Ship (перевод в awaiting_delivery)
    # -----------------------------
    def ship_posting(self, posting_number: str) -> tuple[bool, str | None]:
        logger.info(f"Отправка заказа {posting_number} в awaiting_delivery")

        order_info = self.get_posting_info(posting_number)
        if not order_info:
            logger.error(f"Не удалось получить информацию о заказе {posting_number}")
            return False, "Order info fetch failed"

        payload = self.make_ship_payload(order_info)

        resp = send_request_with_retries(
            url=self.URL_SHIP,
            method="POST",
            headers=self.headers,
            body=payload
        )

        if resp:
            logger.info(f"Заказ {posting_number} успешно отправлен в awaiting_delivery")
            return True, None
        else:
            logger.error(f"Ошибка при ship заказа {posting_number}")
            return False, "Ship failed"
