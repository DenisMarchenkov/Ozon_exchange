from pathlib import Path
from typing import Iterable, List

from Common.base_mailer import BaseMailer


class DispatchMailer(BaseMailer):
    """
    Письмо с наклейками и файлом для сборки заказов.
    """

    def __init__(self, dispatch_files: Iterable[dict], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dispatch_files = list(dispatch_files)

    # -----------------------------------------------
    #               Тема письма
    # -----------------------------------------------
    def build_subject(self) -> str:
        return "Заказы к сбору"

    # -----------------------------------------------
    #               Тело письма
    # -----------------------------------------------
    def build_body(self) -> str:
        if not self.dispatch_files:
            return (
                "Добрый день!\n\n"
                "Файлы для сборки заказов отсутствуют.\n"
            )

        dispatch_id = self.dispatch_files[0].get("dispatch_id")

        label_name = None
        warehouse_name = None

        for file in self.dispatch_files:
            if file.get("file_type") == "LABEL":
                label_name = Path(file["file_path"]).name
            elif file.get("file_type") == "WAREHOUSE":
                warehouse_name = Path(file["file_path"]).name

        lines = [
            "Добрый день!",
            "",
            "Во вложении файлы для сборки заказов.",
        ]

        if dispatch_id:
            lines.append(f"Идентификатор отправки: {dispatch_id}")

        lines.append("")

        if label_name:
            lines.append(f"- Наклейки: {label_name}")

        if warehouse_name:
            lines.append(f"- Файл для склада: {warehouse_name}")

        lines.extend([
            "",
            "Просьба принять в работу.",
        ])

        return "\n".join(lines)

    # -----------------------------------------------
    #               Вложения
    # -----------------------------------------------
    def build_attachments(self) -> List[Path]:
        attachments: List[Path] = []

        for file in self.dispatch_files:
            path = file.get("file_path")
            if not path:
                continue

            attachments.append(Path(path))

        return attachments
