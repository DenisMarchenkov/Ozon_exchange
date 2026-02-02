import time
from pathlib import Path
from Common.logger import get_logger
from Confirmations.api.ozon_labels_api import OzonLabelsAPI, OzonNotReadyError
from Confirmations.db_confirmations.confirmations_repository import ConfirmationsRepository
from Confirmations.services.labels.labels_file_manager import LabelsFileManager
from Common.time import now_iso

logger = get_logger(__name__)


class LabelsGenerator:
    MAX_RETRIES = 5
    CHECK_INTERVALS = [10, 30, 60, 120, 300]  # сек

    def __init__(self):
        self.api = OzonLabelsAPI()
        self.repo = ConfirmationsRepository()
        self.files = LabelsFileManager()

    def download(self, dispatch_id) -> Path | None:
        postings = self.repo.get_postings_by_dispatch(dispatch_id)
        postings = list(set(postings))

        if not postings:
            logger.info("Нет заказов для генерации наклеек")
            return None

        logger.info(f"Генерация наклеек для {len(postings)} заказов")
        self.repo.update_stickers_status(postings, "creating", now_iso())

        # --- RETRY LOGIC FOR CREATION ---
        task_id = None
        # Используем те же интервалы, или свои. Возьмем CHECK_INTERVALS для простоты
        for attempt, interval in enumerate(self.CHECK_INTERVALS, start=1):
            try:
                task_id = self.api.create_task(postings)
                if task_id:
                    break
            except OzonNotReadyError:
                logger.warning(
                    f"Ozon не готов принять задачу (NO_POSTINGS...), попытка {attempt}/{len(self.CHECK_INTERVALS)} через {interval}s"
                )
                time.sleep(interval)
        
        if not task_id:
            logger.error("Не удалось создать задачу на получение наклеек (все попытки исчерпаны).")
            self.repo.update_stickers_status(postings, "error", now_iso())
            return None
        # --------------------------------

        self.repo.update_stickers_status(postings, "in_progress", now_iso())
        result = self._wait_task_with_retry(task_id)

        if result.get("status") == "completed" and result.get("file_url"):
            path = self.files.save_labels(result["file_url"])
            self.repo.update_stickers_status(postings, "ready", now_iso())
            logger.info(f"Наклейки сохранены: {path}")
            return path
        else:
            self.repo.update_stickers_status(postings, "error", now_iso())
            logger.error(f"При генерации наклеек Ozon вернул ошибку {result}")
            return None

    def _wait_task_with_retry(self, task_id: str) -> dict:
        for attempt, interval in enumerate(self.CHECK_INTERVALS, start=1):
            info = self.api.get_task_status(task_id)
            status = info.get("status")

            # Всё готово
            if status == "completed":
                return info

            # Ошибка, которую нельзя исправить
            if status == "error":
                return {"status": "error", "error": "Ошибка на стороне Ozon"}

            # Временная ситуация — OZON ещё не готов
            if info.get("error_code") == "NO_POSTINGS_FOR_BATCH_DOWNLOAD":
                logger.warning(
                    f"OZON ещё не готов, повторная попытка {attempt}/{len(self.CHECK_INTERVALS)} через {interval}s"
                )
            else:
                logger.info(f"Задача наклеек в процессе ({status}), ожидание {interval}s...")

            time.sleep(interval)

        # Если всё retries пройдены
        return {"status": "error", "error": "Таймаут ожидания наклеек или OZON не готов"}
