from typing import Iterable

from Common.base_mailer import BaseMailer


class ShortageMailer(BaseMailer):
    """
    Письмо поставщику с дефектурой.
    """
    def __init__(self, shortage_rows: Iterable[dict], *args, **kwargs):
        """
        :param shortage_rows: список словарей из БД с информацией по позициям с ошибками
        :param args, kwargs: передаются в BaseMailer
        """
        super().__init__(*args, **kwargs)
        self.shortage_rows = list(shortage_rows)

    def build_subject_core(self) -> str:
        return "Обнаружена дефектура в подтверждениях"

    def build_body(self) -> str:
        if not self.shortage_rows:
            return "Добрый день!\n\nОшибок при переводе подтверждений не обнаружено.\n"

        # группируем по posting_number (или confirmation_id, если нужно)
        confirmations = {}
        for row in self.shortage_rows:
            posting_number = row['posting_number']
            confirmations.setdefault(posting_number, []).append(row)

        body_lines = [
            "Добрый день!\n\n"
            "Система OrderGuard выявила позиции, не подтверждённые при обработке заказов.\n\n"
            "В случае невозможности подтверждения просим:\n"
            "— отменить заказ в личном кабинете и удалить товарную операцию в базе поставщика, либо\n"
            "— согласовать замену отказанной позиции.\n\n"
            "Просим проверить фактическое наличие товаров.\n"
            "Если заказ может быть удовлетворён, необходимо предварительно добавить "
            "недостающие позиции в заказ в системе поставщика, "
            "после чего повторно выгрузить файл подтверждения через систему электронного обмена поставщика.\n"
        ]

        for posting_number, items in confirmations.items():
            body_lines.append(f"Подтверждение: {posting_number}")
            for item in items:
                line = (
                    f"----- SKU: {item['sku_code']} / {item['sku_art']}\n"
                    f"----- Наименование: {item['name']}\n"
                    f"----- Кол-во подтвержденных: {item['quantity_confirm']}\n"
                    f"----- Кол-во отказанных: {item['quantity_refused']}\n"
                    f"----- Код подразделения: {item['division_id']}"
                )
                body_lines.append(line)
            body_lines.append("")  # пустая строка между подтверждениями

        return "\n".join(body_lines)
