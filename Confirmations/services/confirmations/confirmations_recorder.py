import pandas as pd

from Common.logger import get_logger
from Confirmations.db_confirmations.confirmations_repository import ConfirmationsRepository
from Confirmations.utils.time import now_iso

logger = get_logger(__name__)


class ConfirmationsRecorder:
    """
    Сервисный слой.

    Отвечает за:
    - чтение DataFrame
    - создание / обновление confirmations
    - перезапись confirmation_items
    - корректный расчёт итогового статуса

    Поддерживает повторный импорт:
    REFUSED → OK
    """

    REQUIRED_COLUMNS = {
        "ORDER_ID",
        "CODEPST",
        "CODEART",
        "NAME",
        "QNT",
        "REFUSED",
        "PODRCD",
    }

    PROTECTED_STATUSES = {"confirmed", "awaiting_delivery"}

    def __init__(self, repo: ConfirmationsRepository):
        self.repo = repo

    def record_from_dataframe(self, df: pd.DataFrame) -> list[str]:
        if df is None or df.empty:
            logger.info("Датафрейм пуст — нечего обрабатывать")
            return []

        missing = self.REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(f"Отсутствуют обязательные колонки: {missing}")

        processed_postings: list[str] = []

        for posting_number_raw, group in df.groupby("ORDER_ID"):
            posting_number: str = str(posting_number_raw)
            processed_postings.append(str(posting_number))
            division_id = int(group["PODRCD"].iloc[0])
            source_file = (
                group["__source_file__"].iloc[0]
                if "__source_file__" in group.columns
                else None
            )

            existing = self.repo.get_by_posting(posting_number)

            # -------------------------------------------------
            # 1. Защищённые статусы — НЕ ТРОГАЕМ
            # -------------------------------------------------
            if existing and existing["status"] in self.PROTECTED_STATUSES:
                logger.info(
                    f"{posting_number} уже в статусе "
                    f"{existing['status']} — пропуск"
                )
                continue

            # -------------------------------------------------
            # 2. Если подтверждение уже есть — обновляем
            # -------------------------------------------------
            if existing:
                confirmation_id = existing["id"]
                logger.info(
                    f"{posting_number} найден (status={existing['status']}) — обновляем"
                )
                self.repo.delete_items_by_confirmation(confirmation_id)

            # -------------------------------------------------
            # 3. Если нет — создаём новое
            # -------------------------------------------------
            else:
                confirmation_id = self.repo.add_confirmation(
                    posting_number=posting_number,
                    division_id=division_id,
                    status="NEW",
                    source_file=source_file,
                    created_at=now_iso(),
                    updated_at=now_iso()
                )
                logger.info(f"{posting_number} создано новое подтверждение")

            # -------------------------------------------------
            # 4. Формируем позиции
            # -------------------------------------------------
            items = []
            has_refused = False

            for _, row in group.iterrows():
                # Определяем статус позиции
                refused = int(row["REFUSED"])
                item_status = "REFUSED" if refused > 0 else "OK"
                if refused > 0:
                    has_refused = True

                items.append((
                    confirmation_id,
                    int(row["CODEPST"]),
                    str(row["CODEART"]),
                    row.get("NAME"),
                    int(row["QNT"]),
                    int(row["REFUSED"]),
                    item_status,
                    float(row["PRICE_WITH_VAT"]),
                    str(row["GTD"]),
                    str(row["DATE_EXPIRATION"]),
                    str(row["BRAND"]),
                    now_iso(),
                    now_iso()
                ))

            self.repo.add_items_bulk(items)

            # -------------------------------------------------
            # 5. Финальный статус подтверждения
            # -------------------------------------------------
            final_status = "awaiting_confirmation" if has_refused else "confirmed"
            self.repo.update_status(posting_number, final_status)

            logger.info(
                f"{posting_number} обработан, итоговый статус: {final_status}"
            )

        logger.info(
            f"Обработка подтверждений завершена. "
            f"Всего обработано: {len(processed_postings)}"
        )

        return processed_postings

