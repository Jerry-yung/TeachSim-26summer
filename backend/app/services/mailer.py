from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.core.config import Settings, get_settings


class MailDeliveryError(RuntimeError):
    pass


def send_text_email(*, to_email: str, subject: str, body: str, settings: Settings | None = None) -> None:
    cfg = settings or get_settings()
    username = (cfg.smtp_username or "").strip()
    password = (cfg.smtp_password or "").strip()
    sender = (cfg.smtp_from or username).strip()
    if not cfg.smtp_host or not username or not password or not sender:
        raise MailDeliveryError("SMTP 配置不完整")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content(body)

    try:
        if cfg.smtp_use_ssl:
            with smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, timeout=20) as server:
                server.login(username, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=20) as server:
                server.ehlo()
                server.login(username, password)
                server.send_message(msg)
    except (OSError, smtplib.SMTPException) as exc:
        raise MailDeliveryError(f"邮件发送失败: {exc}") from exc
