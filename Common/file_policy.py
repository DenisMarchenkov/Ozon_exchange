import re
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class FilePolicy:
    def __init__(
        self,
        *,
        filename_regex: str | None = None,
        ignored_divisions: set[str] | None = None,
        allowed_divisions: set[str] | None = None,
    ):
        """
        filename_regex — regex, которому должно соответствовать имя файла
        ignored_divisions — подразделения, которые нужно игнорировать
        allowed_divisions — если задано, разрешены ТОЛЬКО они
        """

        self.filename_re = re.compile(filename_regex, re.IGNORECASE) if filename_regex else None
        self.ignored_divisions = {str(x) for x in ignored_divisions or set()}
        self.allowed_divisions = {str(x) for x in allowed_divisions or set()}
        self.division_re = re.compile(r"_(\d+)\.xls$", re.IGNORECASE)

    def match(self, file: Path) -> bool:
        name = file.name
        logger.debug(f"Проверка файла: {name}")

        # 1. Маска имени файла
        if self.filename_re:
            if not self.filename_re.search(name):
                logger.info(f"Файл {name} пропущен: не соответствует маске {self.filename_re.pattern}")
                return False
            else:
                logger.debug(f"Файл {name} прошёл проверку маски")

        # 2. Извлекаем подразделение
        match = self.division_re.search(name)
        if not match:
            logger.info(f"Файл {name} пропущен: не найден код подразделения")
            return False

        division_id = match.group(1)
        logger.debug(f"Файл {name}: найден код подразделения {division_id}")

        # 3. Белый список
        if self.allowed_divisions and division_id not in self.allowed_divisions:
            logger.info(f"Файл {name} пропущен: подразделение {division_id} не в allowed_divisions")
            return False

        # 4. Чёрный список
        if division_id in self.ignored_divisions:
            logger.info(f"Файл {name} пропущен: подразделение {division_id} в ignored_divisions")
            return False

        logger.info(f"Файл {name} разрешён для обработки")
        return True

    def filter(self, files: list[Path]) -> list[Path]:
        filtered_files = []
        for f in files:
            if self.match(f):
                filtered_files.append(f)
            else:
                logger.debug(f"Файл {f.name} отфильтрован")
        return filtered_files
