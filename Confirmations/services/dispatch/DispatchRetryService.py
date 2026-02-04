from Common.logger import get_logger


logger = get_logger(__name__)
class DispatchRetryService:
    def __init__(
        self,
        dispatch_repo,
        confirmations_repo,
        files_service,
    ):
        self.dispatch_repo = dispatch_repo
        self.confirmations_repo = confirmations_repo
        self.files_service = files_service

    def retry_failed(self):
        error_dispatches = self.dispatch_repo.get_dispatch_id_by_status("ERROR")

        for dispatch_id in error_dispatches:
            d_id = dispatch_id["id"]
            logger.info(f"Retry {d_id}")
            self.dispatch_repo.update_status(d_id, "RETRYING")

            try:
                missing_files = self.files_service.generate_missing_files(d_id)

                if missing_files:
                    raise RuntimeError(
                        f"После retry отсутствуют файлы: {', '.join(missing_files)}"
                    )

                self.dispatch_repo.update_status(d_id, "PREPARED")
                self.confirmations_repo.mark_dispatch_prepared(d_id)

            except Exception:
                logger.exception(f"Retry не удался для dispatch {d_id}")
                self.dispatch_repo.update_status(d_id, "ERROR")
