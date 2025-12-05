import time
import requests

from typing import Optional, Dict, Any, Union
from requests import Response
from Common.logger import get_logger
from Common.settings import DEV_MODE
from Common.file_utils import get_fake_data

logger = get_logger("Common")

class FakeResponse:
    def __init__(self, status_code: int, json_data=None, text="", headers=None):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text
        self.headers = headers or {}

    def json(self):
        return self._json_data

    @classmethod
    def ok(cls, json_data=None):
        return cls(200, json_data=json_data or {"result": "ok"})


    @classmethod
    def server_error(cls):
        return cls(500, text="Internal Server Error")

    @classmethod
    def too_many_requests(cls, retry_after: int = 1):
        return cls(429, text="Too Many Requests", headers={"Retry-After": str(retry_after)})

    @classmethod
    def not_found(cls, message="Not Found"):
        return cls(404, text=message)


def send_request_with_retries(
    url: str,
    method: str,
    headers: Dict[str, str],
    body: Optional[Dict[str, Any]] = None,
    max_attempts: int = 3
) -> Optional[Dict[str, Any]]:

    attempt = 0
    method = method.upper()

    while attempt < max_attempts:
        try:
            if DEV_MODE:
                response: Union[Response, FakeResponse] = FakeResponse.ok(get_fake_data("fake_response_order.json"))
                # response: Union[Response, FakeResponse] = FakeResponse.too_many_requests(retry_after=2)
                # response: Union[Response, FakeResponse] = FakeResponse.server_error()
                # response: Union[Response, FakeResponse] = FakeResponse.not_found()
            else:
                response: Union[Response, FakeResponse] = requests.request(
                    method=method, url=url, headers=headers, json=body
                )

            if response.status_code == 200:
                logger.info(f"Successfully sent request to {url}")
                return response.json()
            elif 500 <= response.status_code < 600:
                logger.warning(f"Ошибка 5xx ({response.status_code}) — попытка {attempt + 1}/{max_attempts}")
                attempt += 1
                time.sleep(3)
            elif response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 10))
                logger.warning(f"429 Too Many Requests — ждём {retry_after} сек ({attempt + 1}/{max_attempts})")
                time.sleep(retry_after)
                attempt += 1
            else:
                logger.error(f"Ошибка API: {response.status_code} — {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Сетевая ошибка: {e} — попытка {attempt + 1}/{max_attempts}")
            attempt += 1
            time.sleep(3)

    logger.error("Все попытки исчерпаны, запрос не выполнен.")
    return None
