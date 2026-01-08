from Common.logger import get_logger
from Common.time import now_iso
from Prices.utils.file_utils import extract_excel_metadata

logger = get_logger(__name__)


class SupplierPriceGuard:
    """
    Отвечает за проверку:
    изменился ли файл поставщика и нужно ли продолжать обработку.
    """

    def __init__(self, repo, supplier_id: int):
        self.repo = repo
        self.supplier_id = supplier_id

    def check(self, file_path):
        metadata = extract_excel_metadata(
            file_path,
            columns_for_hash=["Артикул", "Price"],
            sort_by="Артикул",
        )

        last_hash = self.repo.get_last_hash(self.supplier_id)

        if last_hash == metadata["file_hash"]:
            logger.warning(
                "Обновление пропущено: файл не изменился (hash=%s)",
                metadata["file_hash"],
            )
            return None

        supplier_price_id = self.repo.save(metadata, self.supplier_id, now_iso())
        logger.info(
            "Зафиксирован новый файл: %s (hash=%s)",
            metadata["name"],
            metadata["file_hash"],
        )
        return metadata, supplier_price_id