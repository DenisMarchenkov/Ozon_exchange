import smtplib
from email.message import EmailMessage
from pathlib import Path
from platform import python_version


def send_email(
    subject: str,
    body: str,
    to: list,
    attachments: list = None,
    sender: str = None,
    smtp_user: str = None,
    smtp_password: str = None,
    smtp_server: str = "smtp.yandex.ru",
    smtp_port: int = 465,
):
    """
    Универсальная отправка писем через SMTP SSL.
    """

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender or smtp_user
    msg["To"] = ", ".join(to)
    msg['Reply-To'] = sender
    msg['Return-Path'] = sender
    msg['X-Mailer'] = 'Python/' + (python_version())
    msg.set_content(body)

    # Вложения
    if attachments:
        for file_path in attachments:
            file_path = Path(file_path)
            with open(file_path, "rb") as f:
                data = f.read()
                msg.add_attachment(
                    data,
                    maintype="application",
                    subtype="octet-stream",
                    filename=file_path.name
                )

    # Отправка
    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(smtp_user, smtp_password)
        server.send_message(msg)