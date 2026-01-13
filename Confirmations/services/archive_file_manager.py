from pathlib import Path
from datetime import datetime
import shutil

from Common.file_policy import FilePolicy
from Common.logger import get_logger

logger = get_logger(__name__)


# class ArchiveFileManager:
#     """
#     Архивирует обработанные файлы, добавляя timestamp к имени.
#     Бизнес-логики не содержит.
#     """
#
#     def __init__(
#         self,
#         inbox_dir: str,
#         archive_dir: str = "archive",
#         file_mask: str = "*.xls",
#         dry_run: bool = False,
#     ):
#         self.inbox_dir = Path(inbox_dir)
#         self.archive_dir = self.inbox_dir / archive_dir
#         self.file_mask = file_mask
#         self.dry_run = dry_run
#
#     def archive_all(self):
#         files = list(self.inbox_dir.glob(self.file_mask))
#
#         if not files:
#             logger.info("ArchiveFileManager: нет файлов для архивирования")
#             return
#
#         self.archive_dir.mkdir(parents=True, exist_ok=True)
#
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#
#         for file in files:
#             dst_name = f"{file.stem}__{timestamp}{file.suffix}"
#             dst = self.archive_dir / dst_name
#
#             if self.dry_run:
#                 logger.info(f"[DRY RUN] {file.name} → {dst.name}")
#                 continue
#
#             try:
#                 shutil.move(file, dst)
#                 logger.info(f"{file.name} → {dst.name}")
#             except Exception as e:
#                 logger.error(f"Ошибка архивирования {file.name}: {e}")

class ArchiveFileManager:
    """
    Архивирует обработанные файлы, добавляя timestamp к имени.
    Бизнес-логики не содержит.
    """
    def __init__(
        self,
        inbox_dir: str,
        archive_dir: str = "archive",
        file_mask: str = "*.xls",
        dry_run: bool = False,
        file_policy: FilePolicy | None = None,
    ):
        self.inbox_dir = Path(inbox_dir)
        self.archive_dir = self.inbox_dir / archive_dir
        self.file_mask = file_mask
        self.dry_run = dry_run
        self.file_policy = file_policy

    def archive_all(self):
        files = list(self.inbox_dir.glob(self.file_mask))

        if self.file_policy:
            files = self.file_policy.filter(files)

        if not files:
            logger.info("ArchiveFileManager: нет файлов для архивирования")
            return

        self.archive_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for file in files:
            dst = self.archive_dir / f"{file.stem}__{timestamp}{file.suffix}"

            if self.dry_run:
                logger.info(f"[DRY RUN] {file.name} → {dst.name}")
                continue

            try:
                shutil.move(file, dst)
                logger.info(f"{file.name} → {dst.name}")
            except Exception as e:
                logger.error(f"Ошибка архивирования {file.name}: {e}")