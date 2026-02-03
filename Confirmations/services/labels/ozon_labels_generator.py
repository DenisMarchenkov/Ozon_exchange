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
        postings = list(dict.fromkeys(postings))

        if not postings:
            logger.info("Нет заказов для генерации наклеек")
            return None

        logger.info(f"Генерация наклеек для {len(postings)} заказов")
        self.repo.update_stickers_status(postings, "creating", now_iso())

        # --- RETRY LOGIC FOR CREATION ---
        task_id = None
        for attempt, interval in enumerate(self.CHECK_INTERVALS, start=1):
            try:
                task_id = self.api.create_task(postings)
                if task_id:
                    break
            except OzonNotReadyError:
                logger.warning(
                    f"Ozon не готов принять задачу (NO_POSTINGS...), "
                    f"попытка {attempt}/{len(self.CHECK_INTERVALS)} через {interval}s"
                )
                time.sleep(interval)

        if not task_id:
            logger.error("Не удалось создать задачу на получение наклеек")
            self.repo.update_stickers_status(postings, "error", now_iso())
            return None
        # --------------------------------

        self.repo.update_stickers_status(postings, "in_progress", now_iso())
        result = self._wait_task_with_retry(task_id)

        if result.get("status") != "completed" or not result.get("file_url"):
            self.repo.update_stickers_status(postings, "error", now_iso())
            logger.error(f"При генерации наклеек Ozon вернул ошибку {result}")
            return None

        file_url = result["file_url"]

        # --- ДОКАЧКА PDF (КЛЮЧЕВОЕ МЕСТО) ---
        last_path: Path | None = None
        last_size = 0

        for attempt in range(1, 11):  # 10 попыток докачки
            path = self.files.save_labels(file_url)

            if not path or not path.exists():
                logger.warning(f"Не удалось сохранить PDF (попытка {attempt})")
                time.sleep(5)
                continue

            size = path.stat().st_size
            logger.info(f"PDF попытка {attempt}: размер {size} байт")

            # Если файл увеличился — Ozon ещё докидывает наклейки
            if size > last_size:
                last_size = size
                last_path = path
                time.sleep(5)
                continue

            # Размер стабилизировался → считаем PDF финальным
            logger.info("PDF стабилизировался, считаем финальным")
            last_path = path
            break

        if not last_path:
            self.repo.update_stickers_status(postings, "error", now_iso())
            logger.error("Не удалось получить финальный PDF с наклейками")
            return None

        self.repo.update_stickers_status(postings, "ready", now_iso())
        logger.info(f"Наклейки сохранены: {last_path}")
        return last_path

    def _wait_task_with_retry(self, task_id: str) -> dict:
        for attempt, interval in enumerate(self.CHECK_INTERVALS, start=1):
            info = self.api.get_task_status(task_id)
            status = info.get("status")
            unprinted = info.get("unprinted_postings", [])

            # Ошибка, которую нельзя исправить
            if status == "error":
                return {"status": "error", "error": "Ошибка на стороне Ozon"}

            # Всё готово, наклейки все сгенерированы
            if status == "completed" and not unprinted:
                return info

            # Задача завершена, но есть пропавшие наклейки
            if status == "completed" and unprinted:
                logger.warning(f"Частично сгенерированы наклейки, пропавшие: {unprinted}")
                info["status"] = "partial"
                return info  # сразу возвращаем, download решит retry

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

