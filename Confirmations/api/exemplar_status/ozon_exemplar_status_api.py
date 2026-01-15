from Common.settings import CLIENT_ID, API_TOKEN
from Common.http_utils import send_request_with_retries


class OzonExemplarStatusAPI:
    """
    Минимальный API-клиент.
    Работает ТОЛЬКО с методом exemplar/status.
    """

    URL_STATUS = (
        "https://api-seller.ozon.ru/v5/fbs/posting/product/exemplar/status"
    )

    def __init__(self):
        self.headers = {
            "Client-Id": CLIENT_ID,
            "Api-Key": API_TOKEN,
            "Content-Type": "application/json",
        }

    def get_status(self, posting_number: str) -> dict:
        """
        Возвращает сырой ответ Ozon.
        """
        return send_request_with_retries(
            url=self.URL_STATUS,
            method="POST",
            headers=self.headers,
            body={"posting_number": posting_number},
        )
