from pathlib import Path
from typing import Iterable, List

from Common.base_mailer import BaseMailer


class DispatchMailer(BaseMailer):
    """
    Письмо с наклейками и файлом для сборки заказов.
    """

    def __init__(self, dispatch_files: Iterable[dict], processing_orders: list = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dispatch_files = list(dispatch_files)
        self.processing_orders = processing_orders or []
        self.dispatch_id = self.dispatch_files[0].get("dispatch_id") if self.dispatch_files else None
        # Если есть, берём только часть после последнего "_"
        self.suffix_for_subject = self.dispatch_id.split("_")[-1] if self.dispatch_id else None

    # -----------------------------------------------
    #               Тема письма
    # -----------------------------------------------
    def build_subject_core(self) -> str:
        count = len(self.processing_orders)
        subject = f"Заказы к сбору ({count} шт.)"
        if self.dispatch_id:
            subject += f" --- {self.suffix_for_subject}"
        return subject

    # -----------------------------------------------
    #               Тело письма
    # -----------------------------------------------
    def build_body(self) -> str:
        if not self.dispatch_files:
            return (
                "Добрый день!\n\n"
                "Файлы для сборки заказов отсутствуют.\n"
            )


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

        if self.dispatch_id:
            lines.append(f"Идентификатор отправки: {self.dispatch_id}")

        lines.append("")

        if label_name:
            lines.append(f"Наклейки: {label_name}")

        if warehouse_name:
            lines.append(f"Файл для склада: {warehouse_name}")
            marking_file_id = (
                warehouse_name
                .removesuffix(".xlsx")
                .replace("warehouse_file__", "marking_file_id__", 1)
            )
            lines.append(f"Идентификатор файла с кодами маркировки: {marking_file_id}")
        lines.append("")

        lines.append("Обработанные отправления:")
        for order in self.processing_orders:
            lines.append(f"----- {order}")


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
