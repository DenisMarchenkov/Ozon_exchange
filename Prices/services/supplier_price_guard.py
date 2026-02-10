from Common.logger import get_logger
from Common.time import now_iso
from Prices.utils.file_utils import extract_excel_metadata_per_sheet

logger = get_logger(__name__)


class SupplierPriceGuard:
    """
    Проверяет, изменился ли файл поставщика (теперь через единый метод метаданных).
    """

    def __init__(self, repo, supplier_id: int):
        self.repo = repo
        self.supplier_id = supplier_id

    def check(self, file_path):
        # Для поставщика пока 1 лист (по умолчанию первый, индекс 0)
        sheets_info = [
            {
                "sheet_name": 0,
                "columns_for_hash": ["Артикул", "Price"],
                "sort_by": ["Артикул"],
            }
        ]

        metadata = extract_excel_metadata_per_sheet(
            file_path,
            sheets_info=sheets_info,
        )

        last_hash = self.repo.get_last_supplier_hash(self.supplier_id)

        if last_hash == metadata["file_hash"]:
            logger.info(
                "Файл поставщика (supplier_id=%s) не изменился, пересчёт не требуется",
                self.supplier_id,
            )
            return None

        supplier_price_id = self.repo.save_supplier_price(
            metadata=metadata,
            supplier_id=self.supplier_id,
            created_at=now_iso(),
        )

        logger.info(
            "Зафиксирован новый файл поставщика %s (hash=%s)",
            metadata["name"],
            metadata["file_hash"],
        )

        return metadata, supplier_price_id


class MarkupFileGuard:
    """
    Проверяет, изменился ли файл наценок (сразу по нескольким листам).
    """

    def __init__(self, repo):
        self.repo = repo

    def check(self, file_path):
        # Описываем структуру листов, которые нужно отслеживать
        sheets_info = [
            {
                "sheet_name": "Global_markup",
                "columns_for_hash": ["Причина", "Дата установки"],
                "sort_by": ["Причина", "Дата установки"],
            },
            {
                "sheet_name": "Manual_markup",
                "columns_for_hash": ["Артикул", "наценка", "Дата установки", "Дата отключения"],
                "sort_by": ["Артикул"],
            },
        ]

        # Извлекаем метаданные по всем листам
        metadata = extract_excel_metadata_per_sheet(
            file_path,
            sheets_info=sheets_info,
        )

        last_hash = self.repo.get_last_markup_hash()

        if last_hash == metadata["file_hash"]:
            logger.info("Файл наценок не изменился (листов: %s)", len(sheets_info))
            return None

        markup_file_id = self.repo.save_markup_file(
            metadata=metadata,
            created_at=now_iso(),
        )

        logger.info(
            "Зафиксирован новый файл наценок %s (hash=%s, листов=%s)",
            metadata["name"],
            metadata["file_hash"],
            len(sheets_info),
        )

        return metadata, markup_file_id
