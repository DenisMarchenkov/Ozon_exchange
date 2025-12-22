from Common.logger import get_logger
from Confirmations.utils.time import now_iso

logger = get_logger(__name__)

# class DispatchPrepareService:
#     def __init__(
#         self,
#         dispatch_repo,
#         confirmations_repo,
#         files_service,
#     ):
#         self.dispatch_repo = dispatch_repo
#         self.confirmations_repo = confirmations_repo
#         self.files_service = files_service
#
#     def prepare(self, dispatch_id: str):
#         logger.info(f"Подготовка dispatch {dispatch_id}")
#
#         if not self.dispatch_repo.exists(dispatch_id):
#             self.dispatch_repo.create_dispatch(dispatch_id, now_iso())
#
#         self.dispatch_repo.update_status(dispatch_id, "IN_PROGRESS")
#
#         try:
#             locked_postings = self.confirmations_repo.lock_postings_for_dispatch(
#                 dispatch_id
#             )
#
#             if not locked_postings:
#                 logger.info(
#                     f"Нет postings для формирования dispatch {dispatch_id} — пропуск"
#                 )
#                 self.dispatch_repo.update_status(dispatch_id, "EMPTY")
#                 return
#
#             logger.info(f"Закреплено postings: {len(locked_postings)}")
#
#             missing_files = self.files_service.generate_missing_files(dispatch_id)
#
#             if missing_files:
#                 raise RuntimeError(
#                     f"Dispatch {dispatch_id} не готов. "
#                     f"Отсутствуют файлы: {', '.join(missing_files)}"
#                 )
#
#             self.dispatch_repo.update_status(dispatch_id, "PREPARED")
#             logger.info(f"Dispatch {dispatch_id} успешно подготовлен")
#
#         except Exception:
#             logger.exception(f"Ошибка при подготовке dispatch {dispatch_id}")
#             self.dispatch_repo.update_status(dispatch_id, "ERROR")
#             raise
class DispatchPrepareService:
    def __init__(
        self,
        dispatch_repo,
        confirmations_repo,
        files_service,
    ):
        self.dispatch_repo = dispatch_repo
        self.confirmations_repo = confirmations_repo
        self.files_service = files_service

    def prepare(self, dispatch_id: str, postings_to_lock: list[str] | None = None):
        logger.info(f"Подготовка dispatch {dispatch_id}")

        if not self.dispatch_repo.exists(dispatch_id):
            self.dispatch_repo.create_dispatch(dispatch_id, now_iso())

        self.dispatch_repo.update_status(dispatch_id, "IN_PROGRESS")

        try:
            # если передан список, блокируем только его, иначе вызываем старый метод
            if postings_to_lock is not None:
                locked_postings = self.confirmations_repo.lock_specific_postings(
                    dispatch_id, postings_to_lock
                )
            else:
                locked_postings = self.confirmations_repo.lock_postings_for_dispatch(
                    dispatch_id
                )

            if not locked_postings:
                logger.info(
                    f"Нет postings для формирования dispatch {dispatch_id} — пропуск"
                )
                self.dispatch_repo.update_status(dispatch_id, "EMPTY")
                return

            logger.info(f"Закреплено postings: {len(locked_postings)}")

            missing_files = self.files_service.generate_missing_files(dispatch_id)

            if missing_files:
                raise RuntimeError(
                    f"Dispatch {dispatch_id} не готов. "
                    f"Отсутствуют файлы: {', '.join(missing_files)}"
                )

            self.dispatch_repo.update_status(dispatch_id, "PREPARED")
            logger.info(f"Dispatch {dispatch_id} успешно подготовлен")

        except Exception:
            logger.exception(f"Ошибка при подготовке dispatch {dispatch_id}")
            self.dispatch_repo.update_status(dispatch_id, "ERROR")
            raise
