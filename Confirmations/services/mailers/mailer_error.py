from typing import Iterable

from Common.base_mailer import BaseMailer


class ErrorMailer(BaseMailer):
    """
    Письмо о том, что произошла ошибка при переводе подтверждений.
    """

    def __init__(self, error_rows: Iterable[dict], *args, **kwargs):
        """
        :param error_rows: список словарей из БД с информацией по позициям с ошибками
        :param args, kwargs: передаются в BaseMailer
        """
        super().__init__(*args, **kwargs)
        self.error_rows = list(error_rows)

    def build_subject(self) -> str:
        return "Ошибка при переводе подтверждений в статус 'ожидает отгрузки' в OZON"

    def build_body(self) -> str:
        if not self.error_rows:
            return "Добрый день!\n\nОшибок при переводе подтверждений не обнаружено.\n"

        # группируем по posting_number (или confirmation_id, если нужно)
        confirmations = {}
        for row in self.error_rows:
            posting_number = row['posting_number']
            confirmations.setdefault(posting_number, []).append(row)

        body_lines = [
            "Добрый день!\n",
            "Вероятно, что при попытке перевести отправление в статус 'ожидает отгрузки', произошла ошибка ",
            "Следующие отправления остались не обработанными:\n"
        ]

        for posting_number, items in confirmations.items():
            body_lines.append(f"Подтверждение: {posting_number}")
            for item in items:
                line = (
                    f"----- SKU: {item['sku_code']} / {item['sku_art']}\n"
                    f"----- Наименование: {item['name']}\n"
                    f"----- Кол-во: {item['quantity_confirm']}\n"
                    f"----- Ответ от Озон: {item['error_message']}\n"
                    f"----- Код подразделения: {item['division_id']}"
                )
                body_lines.append(line)
            body_lines.append("")  # пустая строка между подтверждениями

        return "\n".join(body_lines)