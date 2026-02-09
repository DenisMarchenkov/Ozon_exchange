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
    CHECK_INTERVALS = [10, 30, 60, 120]  # сек
    def __init__(self):
        self.api = OzonLabelsAPI()
        self.repo = ConfirmationsRepository()
        self.files = LabelsFileManager()

    def download(self, dispatch_id) -> "LabelsResult":
        # Инициализируем репозиторий Dispatch для работы с задачами, если нужно
        # (в идеале внедрять зависимости, но здесь создадим)
        from Confirmations.db_confirmations.dispatch_repository import DispatchRepository
        from Common.db.database import Database
        from Common.settings import DB_PATH
        dispatch_repo = DispatchRepository(Database(DB_PATH))

        postings = self.repo.get_postings_by_dispatch(dispatch_id)
        postings = list(dict.fromkeys(postings))
        postings.sort()  # <--- Гарантируем сортировку по номеру отправления

        if not postings:
            logger.info("Нет заказов для генерации наклеек")
            return LabelsResult(None, [], [], False)

        logger.info(f"Генерация наклеек для {len(postings)} заказов")

        # 1. Проверяем, есть ли уже активная задача
        stored_task_id = dispatch_repo.get_ozon_task_id(dispatch_id)
        task_id = stored_task_id

        # 2. Если нет задачи — создаём
        if not task_id:
            self.repo.update_stickers_status(postings, "creating", now_iso())
            
            # --- RETRY LOGIC FOR CREATION ---
            for attempt, interval in enumerate(self.CHECK_INTERVALS, start=1):
                try:
                    task_id = self.api.create_task(postings)
                    if task_id:
                        dispatch_repo.update_ozon_task_id(dispatch_id, task_id)
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
                return LabelsResult(None, [], postings, False)
            # --------------------------------
        else:
            logger.info(f"Найдена активная задача Ozon: {task_id}, пропускаем создание")

        self.repo.update_stickers_status(postings, "in_progress", now_iso())
        
        # 3. Ждем результат
        result = self._wait_task_with_retry(task_id)

        if not result.get("file_url"):
            # Если даже ссылки нет — это полный провал (или error)
            # Но если статус partial, ссылка должна быть...
            # Если error:
            self.repo.update_stickers_status(postings, "error", now_iso())
            logger.error(f"При генерации наклеек Ozon вернул ошибку или нет ссылки: {result}")
            return LabelsResult(None, [], postings, False)

        # 4. Анализ результата (успешные vs неуспешные)
        unprinted_list = result.get("unprinted_postings", [])
        unprinted_numbers = {
            item.get('posting_number') for item in unprinted_list if isinstance(item, dict)
        }
        
        failed_postings = [p for p in postings if p in unprinted_numbers]
        successful_postings = [p for p in postings if p not in unprinted_numbers]

        # Логируем и обновляем статусы
        if failed_postings:
            logger.warning(f"Не удалось распечатать {len(failed_postings)} наклеек")
            self.repo.update_stickers_status(failed_postings, "error", now_iso())
        
        if successful_postings:
            # Для успешных статус 'ready' поставим после скачивания файла
            pass
        else:
            logger.error("Нет успешных наклеек для скачивания (все в unprinted)")
            return LabelsResult(None, [], failed_postings, False)


        file_url = result["file_url"]

        # --- ДОКАЧКА PDF ---
        last_path: Path | None = None
        last_size = 0

        for attempt in range(1, 11):
            path = self.files.save_labels(file_url)

            if not path or not path.exists():
                logger.warning(f"Не удалось сохранить PDF (попытка {attempt})")
                time.sleep(5)
                continue

            size = path.stat().st_size
            logger.info(f"PDF попытка {attempt}: размер {size} байт")

            if size > last_size:
                last_size = size
                last_path = path
                time.sleep(5)
                continue

            logger.info("PDF стабилизировался, считаем финальным")
            last_path = path
            break

        if not last_path:
            self.repo.update_stickers_status(successful_postings, "error", now_iso())
            logger.error("Не удалось получить финальный PDF с наклейками")
            # Считаем, что успешные стали неуспешными из-за скачивания
            return LabelsResult(None, [], postings, False)

        # Финальный успех для successful_postings
        self.repo.update_stickers_status(successful_postings, "ready", now_iso())
        logger.info(f"Наклейки сохранены: {last_path}")
        
        is_partial = bool(failed_postings)
        return LabelsResult(last_path, successful_postings, failed_postings, is_partial)

    def _wait_task_with_retry(self, task_id: str) -> dict:
        last_partial_result = None

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

            # Задача завершена, но есть пропавшие наклейки (статус completed или partial)
            if (status == "completed" and unprinted) or status == "partial":
                logger.warning(
                    f"Частично сгенерированы наклейки (статус {status}), пропавшие: {len(unprinted)}. "
                    f"Ждем, возможно Ozon доработает. Попытка {attempt}."
                    f"Сырой ответ {unprinted}"
                )
                last_partial_result = info
            
            # Временная ситуация — OZON ещё не готов
            elif info.get("error_code") == "NO_POSTINGS_FOR_BATCH_DOWNLOAD":
                logger.warning(
                    f"OZON ещё не готов, повторная попытка {attempt}/{len(self.CHECK_INTERVALS)} через {interval}s"
                )
            else:
                logger.info(f"Задача наклеек в процессе ({status}), ожидание {interval}s...")

            time.sleep(interval)

        # Если всё retries пройдены
        if last_partial_result:
            logger.warning("Таймаут ожидания. Возвращаем частичный результат.")
            last_partial_result["status"] = "partial"
            return last_partial_result

        return {"status": "error", "error": "Таймаут ожидания наклеек или OZON не готов"}


class LabelsResult:
    def __init__(self, file_path, successful, failed, is_partial):
        self.file_path = file_path
        self.successful = successful
        self.failed = failed
        self.is_partial = is_partial



