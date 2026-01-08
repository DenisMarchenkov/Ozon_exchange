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
    Добавляет shop_name в тему письма по умолчанию.
    """

    #DEFAULT_SHOP_NAME = "OZON"  # <-- здесь можно указать магазин по умолчанию

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
    # Методы, которые нужно определить в наследниках
    # -----------------------------------------------
    @abstractmethod
    def build_body(self) -> str:
        """Тело письма — обязателен к переопределению"""
        pass

    def build_subject_core(self) -> str:
        """
        Основная тема письма.
        Необязательная переопределяемая часть.
        По умолчанию возвращает generic-тему.
        """
        return "Обновление данных для отправлений"

    def build_subject(self) -> str:
        """
        Полная тема письма с названием магазина.
        Все наследники будут автоматически использовать shop_name.
        """
        return f"[{NAME_SHOP}] {self.build_subject_core()}"

    # -----------------------------------------------
    # Вложения (можно переопределить)
    # -----------------------------------------------
    def build_attachments(self) -> List[Path]:
        return []

    # -----------------------------------------------
    # Подпись письма
    # -----------------------------------------------
    def build_signature(self) -> str:
        return (
            "\n\n\n"
            "OrderGuard\n"
            "Система контроля заказов\n"
            "Это письмо сформировано автоматически"
        )

    # -----------------------------------------------
    # Основной процесс отправки
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
