import requests
from typing import Iterable

from Common.http_utils import send_request_with_retries
from Common.logger import get_logger
from Common.settings import CLIENT_ID, API_TOKEN

logger = get_logger(__name__)


class OzonNotReadyError(Exception):
    pass


class OzonLabelsAPI:
    """
    Работа с API Ozon для генерации и получения наклеек (FBS).
    Только HTTP, без ожиданий и бизнес-логики.
    """

    CREATE_URL = "https://api-seller.ozon.ru/v2/posting/fbs/package-label/create"
    GET_URL = "https://api-seller.ozon.ru/v1/posting/fbs/package-label/get"

    def __init__(self):
        self.headers = {
            "Client-Id": CLIENT_ID,
            "Api-Key": API_TOKEN,
            "Content-Type": "application/json",
        }

    # -------------------------------------------------
    # Создание задачи
    # -------------------------------------------------

    def create_task(self, posting_numbers: Iterable[str]) -> str | None:
        data = {"posting_number": list(posting_numbers)}

        try:
            resp = send_request_with_retries(
                url=self.CREATE_URL,
                method="POST",
                headers=self.headers,
                body=data,
                accepted_status_codes=[200, 400]
            )
            if not resp:
                logger.error("Ozon не вернул response при создании наклеек")
                return None

            # Проверка на ошибку "ещё не готово" when 400
            result_msg = resp.get("message")
            if resp.get("code") == 3 and result_msg:
                if result_msg == "NO_POSTINGS_FOR_BATCH_DOWNLOAD":
                    raise OzonNotReadyError(
                        "Ozon not ready: NO_POSTINGS_FOR_BATCH_DOWNLOAD"
                    )

            tasks = resp.get("result", {}).get("tasks", [])
            if not tasks:
                # Если вернулся 200, но тасков нет — это тоже странно, но логируем
                # Если была ошибка 400, "result" может не быть.
                if "error" in resp or "code" in resp:
                     logger.error(f"Ozon вернул ошибку при создании наклеек: {resp}")
                     return None

                logger.error("Ozon не вернул tasks при создании наклеек")
                return None

            task_id = next(
                (task['task_id'] for task in tasks if task['task_type'] == 'small_label'),
                None)

            if not task_id:
                logger.error("task_id отсутствует в ответе Ozon")
                return None

            logger.info(f"Создана задача наклеек: task_id={task_id}")
            return task_id

        except requests.RequestException:
            logger.exception("Ошибка при создании задачи наклеек")
            return None

    # -------------------------------------------------
    # Проверка статуса
    # -------------------------------------------------

    def get_task_status(self, task_id: str) -> dict:
        response = send_request_with_retries(
            url=self.GET_URL,
            method="POST",
            headers=self.headers,
            body={"task_id": task_id},
        )

        if not response:
            return {"status": "error"}

        result = response.get("result", {})
        status = result.get("status")
        file_url = result.get("file_url")
        printed_count = result.get("printed_postings_count")
        unprinted = result.get("unprinted_postings", [])

        if status == "completed" and file_url:
            return {
                "status": "completed",
                "file_url": file_url,
                "printed_postings_count": printed_count,
                "unprinted_postings": unprinted,
            }

        if status in {"pending", "in_progress", "completed"}:
            # completed, но без файла — ЖДЁМ
            return {"status": "in_progress"}

        return {"status": "error"}

