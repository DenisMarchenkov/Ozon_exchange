# from Common.http_utils import send_request_with_retries
# from Common.settings import CLIENT_ID, API_TOKEN
# from Common.logger import get_logger
#
# logger = get_logger("ConfirmationsAPI")
#
#
# class OzonConfirmationsAPI:
#     """
#     Клиент Ozon API для перевода заказов (posting_number)
#     в статус awaiting_delivery.
#     """
#
#     URL_GET = "https://api-seller.ozon.ru/v3/posting/fbs/get"
#     URL_SHIP = "https://api-seller.ozon.ru/v4/posting/fbs/ship"
#
#     def __init__(self):
#         self.headers = {
#             "Client-Id": CLIENT_ID,
#             "Api-Key": API_TOKEN,
#             "Content-Type": "application/json"
#         }
#
#     # -----------------------------
#     # Получение полной структуры заказа
#     # -----------------------------
#     def get_posting_info(self, posting_number: str):
#         body = {
#             "posting_number": posting_number,
#             "with": {
#                 "analytics_data": False,
#                 "barcodes": False,
#                 "financial_data": False,
#                 "product_exemplars": False,
#                 "translit": False,
#             }
#         }
#
#         logger.info(f"Получение данных заказа {posting_number}")
#
#         response = send_request_with_retries(
#             url=self.URL_GET,
#             method="POST",
#             headers=self.headers,
#             body=body,
#         )
#         return response
#
#     # -----------------------------
#     # Преобразование данных заказа
#     # в формат ship-запроса
#     # -----------------------------
#     @staticmethod
#     def make_ship_payload(order_json: dict) -> dict:
#         """
#         order_json — это ответ от v3/posting/fbs/get
#         Возвращаем структуру:
#         {
#            "posting_number": "...",
#            "packages": [
#               {"products": [{"sku":..., "quantity":...}, ...]}
#            ]
#         }
#         """
#
#         posting_number = order_json["result"]["posting_number"]
#
#         products = []
#         for item in order_json["result"]["products"]:
#             products.append({
#                 "sku": item["sku"],
#                 "quantity": item["quantity"]
#             })
#
#         return {
#             "posting_number": posting_number,
#             "packages": [
#                 {"products": products}
#             ]
#         }
#
#     # -----------------------------
#     # Ship (перевод в awaiting_delivery)
#     # -----------------------------
#     def ship_posting(self, posting_number: str) -> tuple[bool, str | None]:
#         logger.info(f"Отправка заказа {posting_number} в awaiting_delivery")
#
#         order_info = self.get_posting_info(posting_number)
#         if not order_info:
#             logger.error(f"Не удалось получить информацию о заказе {posting_number}")
#             return False, "Order info fetch failed"
#
#         payload = self.make_ship_payload(order_info)
#
#         resp = send_request_with_retries(
#             url=self.URL_SHIP,
#             method="POST",
#             headers=self.headers,
#             body=payload
#         )
#
#         if resp:
#             logger.info(f"Заказ {posting_number} успешно отправлен в awaiting_delivery")
#             return True, None
#         else:
#             logger.error(f"Ошибка при ship заказа {posting_number}")
#             return False, "Ship failed"



from Common.logger import get_logger
from Common.settings import CLIENT_ID, API_TOKEN
from Common.http_utils import send_request_with_retries

logger = get_logger("OzonConfirmationsAPI")


class OzonAPIError(Exception):
    """Ошибка при работе с Ozon API."""


class OzonResponseError(Exception):
    """Ошибка, которую вернул сам Ozon (message, code)."""


class OzonConfirmationsAPI:
    """
    Клиент Ozon API для операции ship (перевод в awaiting_delivery).
    Чистая версия — без fake режима.
    """

    URL_GET = "https://api-seller.ozon.ru/v3/posting/fbs/get"
    URL_SHIP = "https://api-seller.ozon.ru/v4/posting/fbs/ship"

    def __init__(self):
        self.headers = {
            "Client-Id": CLIENT_ID,
            "Api-Key": API_TOKEN,
            "Content-Type": "application/json",
        }

    # ----------------------------------------------------------------------
    # Универсальный парсер ответа
    # ----------------------------------------------------------------------
    @staticmethod
    def parse_response(resp: dict) -> dict:
        """
        Проверяет ответ Ozon — если есть "message" и нет "result", значит это ошибка.
        """
        if not isinstance(resp, dict):
            raise OzonAPIError(f"Некорректный формат ответа от API: {resp}")

        # Ошибка от Ozon
        if "message" in resp and "result" not in resp:
            raise OzonResponseError(resp.get("message", "Неизвестная ошибка"))

        return resp

    # ----------------------------------------------------------------------
    # GET информации о заказе
    # ----------------------------------------------------------------------
    def get_posting_info(self, posting_number: str) -> dict:
        logger.info(f"Получение данных заказа {posting_number}")

        body = {
            "posting_number": posting_number,
            "with": {
                "analytics_data": False,
                "barcodes": False,
                "financial_data": False,
                "product_exemplars": False,
                "translit": False,
            },
        }

        resp = send_request_with_retries(
            url=self.URL_GET,
            method="POST",
            headers=self.headers,
            body=body,
        )

        parsed = self.parse_response(resp)

        try:
            return parsed["result"]
        except KeyError:
            raise OzonAPIError("Ответ Ozon не содержит поля result")

    # ----------------------------------------------------------------------
    # Построение payload для ship
    # ----------------------------------------------------------------------
    @staticmethod
    def make_ship_payload(order_json: dict) -> dict:
        """
        Формирует payload для ship-запроса из структуры заказа.
        """
        try:
            posting_number = order_json["posting_number"]
            products_raw = order_json["products"]
        except KeyError as e:
            raise OzonAPIError(f"Ошибка структуры данных: нет ключа {e}")

        products = []
        for item in products_raw:
            try:
                products.append({
                    "sku": item["sku"],
                    "quantity": item["quantity"],
                })
            except KeyError as e:
                raise OzonAPIError(f"Ошибка структуры product: нет ключа {e}")

        return {
            "posting_number": posting_number,
            "packages": [{"products": products}],
        }

    # ----------------------------------------------------------------------
    # SHIP — перевод заказа в awaiting_delivery
    # ----------------------------------------------------------------------
    def ship_posting(self, posting_number: str) -> tuple[bool, str | None]:
        logger.info(f"Начинаем ship заказа {posting_number}")

        # 1. Получаем данные заказа
        try:
            order_raw = self.get_posting_info(posting_number)
        except Exception as e:
            logger.error(f"Ошибка получения данных заказа {posting_number}: {e}")
            return False, str(e)

        # 2. Формируем payload
        try:
            payload = self.make_ship_payload(order_raw)
        except Exception as e:
            logger.error(f"Ошибка формирования payload для {posting_number}: {e}")
            return False, str(e)

        # 3. Ship запрос
        resp = send_request_with_retries(
            url=self.URL_SHIP,
            method="POST",
            headers=self.headers,
            body=payload,
        )

        # 4. Проверяем ответ
        try:
            parsed = self.parse_response(resp)
        except OzonResponseError as e:
            logger.error(f"Ozon вернул ошибку ship для {posting_number}: {e}")
            return False, str(e)
        except Exception as e:
            logger.error(f"Некорректный ответ при ship {posting_number}: {e}")
            return False, str(e)

        # 5. Проверяем успешность ship
        if "result" in parsed:
            logger.info(f"Заказ {posting_number} успешно переведён в awaiting_delivery")
            return True, None

        logger.error(f"Неожиданная структура ответа ship: {parsed}")
        return False, "Неожиданная структура ответа от Ozon"
