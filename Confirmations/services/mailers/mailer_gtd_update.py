from Common.base_mailer import BaseMailer

class GTDAutoUpdateMailer(BaseMailer):
    """
    Письмо-уведомление о попытке автоматического обновления GTD для отправлений.
    """
    def __init__(self, postings: list[dict], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.postings = postings

    def build_subject_core(self) -> str:
        return "Автообновление GTD для отправлений OZON"

    def build_body(self) -> str:
        if not self.postings:
            return "Добрый день!\n\nНет отправлений для автообновления GTD.\n"

        body_lines = [
            "Добрый день!\n\n"
            "Система OrderGuard пытается автоматически обновить GTD для следующих отправлений OZON:\n"
        ]

        for p in self.postings:
            body_lines.append(
                f"— Отправление: {p['posting_number']}\n"
                f"   Статус: {p['status']}\n"
                f"   Файл подтверждения: {p['source_file']}\n"
                f"   Код подразделения: {p['division_id']}\n"
            )

        body_lines.append(
            "\nЕсли GTD отсутствует или некорректен, необходимо проверить данные "
            "и при необходимости исправить вручную.\n"
            "Данные отправления будут обработаны в следующий сеанс обмена данными, согласно расписанию."
        )

        return "\n".join(body_lines)