from abc import ABC, abstractmethod
from pathlib import Path
from typing import List
from Common.logger import get_logger
from Common.email_utils import send_email

logger = get_logger("BaseMailer")


class BaseMailer(ABC):
    """
    Базовый класс для всех писем.
    """

    def __init__(
        self,
        to: List[str],
        smtp_user: str,
        smtp_password: str,
        sender: str = None
    ):
        self.to = to
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.sender = sender or smtp_user

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

    # -----------------------------------------------
    #               Основной процесс отправки
    # -----------------------------------------------
    def send(self):
        subject = self.build_subject()
        body = self.build_body()
        attachments = self.build_attachments()

        logger.info(f"Отправка письма: {subject}")

        send_email(
            subject=subject,
            body=body,
            to=self.to,
            attachments=attachments,
            sender=self.sender,
            smtp_user=self.smtp_user,
            smtp_password=self.smtp_password
        )

        logger.info("Письмо отправлено.")