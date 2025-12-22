import time
from abc import ABC, abstractmethod
from email.utils import formataddr
from pathlib import Path
from typing import List
from Common.logger import get_logger
from Common.email_utils import send_email
from Common.settings import MAILER_LOGIN, MAILER_PASSWORD, RECIPIENT_ADMIN

logger = get_logger(__name__)


class BaseMailer(ABC):
    """
    Базовый класс для всех писем.
    """

    def __init__(
        self,
        to: List[str] = RECIPIENT_ADMIN,
        smtp_user: str = MAILER_LOGIN,
        smtp_password: str = MAILER_PASSWORD,
        sender: str = "OrderGuard"
    ):
        self.to = to
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.sender = formataddr((sender, smtp_user))
    # -----------------------------------------------
    #           Методы, которые нужно определить
    # -----------------------------------------------
    @abstractmethod
    def build_subject(self) -> str:
        pass

    @abstractmethod
    def build_body(self) -> str:
        pass

    def build_attachments(self) -> List[Path]:
        """Можно переопределить, если есть вложения"""
        return []

    def build_signature(self) -> str:
        return (
            "\n\n\n"
            "OrderGuard\n"
            "Система контроля заказов Ozon\n"
            "Это письмо сформировано автоматически"
        )

    # -----------------------------------------------
    #               Основной процесс отправки
    # -----------------------------------------------
    def send(self):
        subject = self.build_subject()
        body = self.build_body()
        attachments = self.build_attachments()

        full_body = body + self.build_signature()

        logger.info(f"Отправка письма: {subject}")

        send_email(
            subject=subject,
            body=full_body,
            to=self.to,
            attachments=attachments,
            sender=self.sender,
            smtp_user=self.smtp_user,
            smtp_password=self.smtp_password
        )
        time.sleep(4)
        logger.info("Письмо отправлено.")