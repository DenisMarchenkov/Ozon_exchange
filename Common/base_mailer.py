import time
from abc import ABC, abstractmethod
from email.utils import formataddr
from pathlib import Path
from typing import List
from Common.logger import get_logger
from Common.email_utils import send_email
from Common.settings import MAILER_LOGIN, MAILER_PASSWORD, RECIPIENT_ADMIN, NAME_SHOP

logger = get_logger(__name__)


class BaseMailer(ABC):
    """
    Базовый класс для всех писем.
    Поддерживает plain-text + HTML.
    """

    def __init__(
        self,
        to: List[str] = RECIPIENT_ADMIN,
        smtp_user: str = MAILER_LOGIN,
        smtp_password: str = MAILER_PASSWORD,
        sender: str = "OrderGuard",
    ):
        self.to = to
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.sender = formataddr((sender, smtp_user))

    # ---------- Обязательные / переопределяемые ----------

    @abstractmethod
    def build_body(self) -> str:
        """Plain-text тело письма"""
        pass

    def build_body_html(self) -> str | None:
        """HTML тело письма (опционально)"""
        return None

    def build_subject_core(self) -> str:
        return "Обновление данных для отправлений"

    def build_attachments(self) -> List[Path]:
        return []

    def build_signature(self) -> str:
        return (
            "\n\n\n"
            "OrderGuard\n"
            "Система контроля заказов\n"
            "Это письмо сформировано автоматически"
        )

    def build_signature_html(self) -> str:
        """
        HTML-подпись для письма.
        Используется для HTML версии письма.
        """
        return """
        <p style="margin-top:40px; font-size:12px; color:#666;">
            <b>OrderGuard</b><br>
            Система контроля заказов<br>
            Это письмо сформировано автоматически
        </p>
        """

    # ---------- Внутренняя логика ----------

    def build_subject(self) -> str:
        return f"[{NAME_SHOP}] {self.build_subject_core()}"

    def send(self):
        subject = self.build_subject()

        text_body = self.build_body() + self.build_signature()
        html_body = self.build_body_html()

        attachments = self.build_attachments()

        logger.info(f"Отправка письма: {subject}")

        send_email(
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            to=self.to,
            attachments=attachments,
            sender=self.sender,
            smtp_user=self.smtp_user,
            smtp_password=self.smtp_password,
        )

        time.sleep(4)
        logger.info("Письмо отправлено")
