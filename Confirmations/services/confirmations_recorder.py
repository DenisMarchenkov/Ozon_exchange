from Confirmations.db_confirmations.confirmations_repository import ConfirmationsRepository
from Common.logger import get_logger

logger = get_logger("Confirmations - confirmations_recorder.py")


class ConfirmationsRecorder:
    """
    Сервис для обработки подтверждений.
    Принимает два датафрейма: ok_df и refused_df
    """

    def __init__(self):
        self.repo = ConfirmationsRepository()

    def process_confirmations(self, ok_df, refused_df, source_file=None):
        """
        Обрабатывает датафреймы OK и REFUSED.
        Создаёт подтверждения и позиции в базе.
        Возвращает список всех posting_number, которые были обработаны.
        """
        processed_postings = []

        # ----------- Обрабатываем OK -----------
        if ok_df is not None and not ok_df.empty:
            for posting_number in ok_df["ORDER_ID"].unique():
                if self.repo.get_by_posting(posting_number):
                    logger.info(f"[OK] Подтверждение {posting_number} уже есть в базе — пропускаем")
                    continue

                # Создаём подтверждение
                conf_id = self.repo.add_confirmation(posting_number, status="confirmed")
                processed_postings.append(posting_number)

                # Добавляем позиции
                for _, row in ok_df[ok_df["ORDER_ID"] == posting_number].iterrows():
                    self.repo.add_item(
                        confirmation_id=conf_id,
                        sku=row.get("CODEART", ""),
                        name=row.get("NAME", ""),
                        quantity=row.get("QNT"),
                        item_status="OK"
                    )

        # ----------- Обрабатываем REFUSED -----------
        if refused_df is not None and not refused_df.empty:
            for posting_number in refused_df["ORDER_ID"].unique():
                if self.repo.get_by_posting(posting_number):
                    logger.info(f"[REFUSED] Подтверждение {posting_number} уже есть в базе — пропускаем")
                    continue

                conf_id = self.repo.add_confirmation(posting_number, status="awaiting_confirmation")
                processed_postings.append(posting_number)

                for _, row in refused_df[refused_df["ORDER_ID"] == posting_number].iterrows():
                    self.repo.add_item(
                        confirmation_id=conf_id,
                        sku=row.get("CODEART", ""),
                        name=row.get("NAME", ""),
                        quantity=row.get("QNT"),
                        item_status="REFUSED"
                    )

        logger.info(f"Обработано подтверждений: {len(processed_postings)}")
        return processed_postings

    def get_last_confirmations(self, limit=50):
        """
        Получить последние подтверждения.
        """
        return self.repo.get_all()
