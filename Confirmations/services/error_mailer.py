from pathlib import Path
from Common.base_mailer import BaseMailer


class ErrorMailer(BaseMailer):
    """
    Письмо о том что произошла ошибка.
    """
    def __init__(self, bad_confirmations, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bad_confirmations = bad_confirmations

    def build_subject(self) -> str:
        return f"При переводе заказов в статут, произошла ошибка"

    def build_body(self) -> str:
        return (
            f"Добрый день!\n\n"
            f"При переводе заказа {self.bad_confirmations} в личном кабинете OZON, произошла ошибка:\n"
            "\n"
        )


