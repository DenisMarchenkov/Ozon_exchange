import smtplib
from email.message import EmailMessage
from pathlib import Path
from platform import python_version
from typing import List

from Common.settings import MAILER_SERVER_SMTP, MAILER_PORT_SMTP

MAILER_PORT_SMTP_INT =int(MAILER_PORT_SMTP)

def send_email(
    *,
    subject: str,
    text_body: str,
    html_body: str | None,
    to: List[str],
    attachments: List[Path] | None = None,
    sender: str,
    smtp_user: str,
    smtp_password: str,
    smtp_server: str = MAILER_SERVER_SMTP,
    smtp_port: int = MAILER_PORT_SMTP_INT,
):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(to)
    msg["Reply-To"] = sender
    msg["Return-Path"] = sender
    msg["X-Mailer"] = "Python/" + python_version()

    # plain-text обязателен всегда
    msg.set_content(text_body)

    # HTML — опционально
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    # вложения
    if attachments:
        for file_path in attachments:
            file_path = Path(file_path)
            with open(file_path, "rb") as f:
                msg.add_attachment(
                    f.read(),
                    maintype="application",
                    subtype="octet-stream",
                    filename=file_path.name,
                )

    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(smtp_user, smtp_password)
        server.send_message(msg)