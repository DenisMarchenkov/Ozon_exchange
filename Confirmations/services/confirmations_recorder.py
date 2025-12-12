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
                podrcd = int(ok_df.loc[ok_df["ORDER_ID"] == posting_number, "PODRCD"].iloc[0])

                if self.repo.get_by_posting(posting_number):
                    logger.info(f"[OK] Подтверждение {posting_number} уже есть в базе — пропускаем")
                    continue

                # Создаём подтверждение
                conf_id = self.repo.add_confirmation(posting_number, status="confirmed", division_id=podrcd)
                processed_postings.append(posting_number)

                # Добавляем позиции
                for _, row in ok_df[ok_df["ORDER_ID"] == posting_number].iterrows():
                    self.repo.add_item(
                        confirmation_id=conf_id,
                        sku_art=row.get("CODEART", ""),
                        name=row.get("NAME", ""),
                        quantity_confirm=row.get("QNT"),
                        item_status="OK",
                        sku_code=row.get("CODEPST"),
                        quantity_refused=row.get("REFUSED"),
                        # brand=row.get("BRAND"),
                        # price_with_vat=row.get("PRICE_WITH_VAT"),
                        # date_expiration=row.get("DATE_EXPIRATION"),
                        # division_id=row.get("PODRCD"),
                        # date_order=row.get("DATE_ORDER"),
                        # date_ship=row.get("DATE_SHIP")

                    )

        # ----------- Обрабатываем REFUSED -----------
        if refused_df is not None and not refused_df.empty:
            for posting_number in refused_df["ORDER_ID"].unique():
                if self.repo.get_by_posting(posting_number):
                    logger.info(f"[REFUSED] Подтверждение {posting_number} уже есть в базе — пропускаем")
                    continue
                podrcd = int(refused_df.loc[refused_df["ORDER_ID"] == posting_number, "PODRCD"].iloc[0])
                conf_id = self.repo.add_confirmation(posting_number, status="awaiting_confirmation", division_id=podrcd)
                processed_postings.append(posting_number)

                for _, row in refused_df[refused_df["ORDER_ID"] == posting_number].iterrows():
                    self.repo.add_item(
                        confirmation_id=conf_id,
                        sku_art=row.get("CODEART", ""),
                        name=row.get("NAME", ""),
                        quantity_confirm=row.get("QNT"),
                        item_status="REFUSED",
                        sku_code = row.get("CODEPST"),
                        quantity_refused=row.get("REFUSED"),
                        # brand = row.get("BRAND"),
                        # price_with_vat = row.get("PRICE_WITH_VAT"),
                        # date_expiration = row.get("DATE_EXPIRATION"),
                        # division_id = row.get("PODRCD"),
                        # date_order = row.get("DATE_ORDER"),
                        # date_ship = row.get("DATE_SHIP")
                    )

        logger.info(f"Обработано подтверждений: {len(processed_postings)}")
        return processed_postings

    def get_last_confirmations(self, limit=50):
        """
        Получить последние подтверждения.
        """
        return self.repo.get_all()
