from pathlib import Path
from Common.base_mailer import BaseMailer


class DefecturaMailer(BaseMailer):
    """
    Письмо поставщику с дефектурой.
    """
    def __init__(self, df, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.df = df

    def build_subject(self) -> str:
        return "Обнаружена дефектура в подтверждениях"

    def build_body(self) -> str:
        return (
            "Добрый день!\n\n"
            "Отправляем список неподтверждённых позиций.\n"
            "Пожалуйста, проверьте наличие и обновите статус.\n"
        )

    def build_attachments(self):
        tmp_file = Path("defectura.xlsx")
        self.df.to_excel(tmp_file, index=False)
        return [tmp_file]