from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Optional, Protocol, runtime_checkable

from django.conf import settings

logger = logging.getLogger(__name__)



@dataclass(frozen=True)
class SMTPConfig:
    host: str = getattr(settings, "SMTP_HOST", "smtp.gmail.com")
    port: int = int(getattr(settings, "SMTP_PORT", 587))
    use_tls: bool = bool(getattr(settings, "SMTP_USE_TLS", True))
    user: Optional[str] = getattr(settings, "SMTP_DEFAULT_USER", "") or None
    password: Optional[str] = getattr(settings, "SMTP_DEFAULT_PASSWORD", "") or None
    timeout_sec: int = 30


@dataclass(frozen=True)
class EmailContent:
    to: list[str]
    subject: str
    body: str
    from_email: Optional[str] = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com")
    is_html: bool = False


@runtime_checkable
class EmailTransport(Protocol):
    """Интерфейс транспорта отправки писем."""
    def send(self, content: EmailContent) -> bool: ...


@runtime_checkable
class UserWithEmail(Protocol):
    """Минимальные ожидания от объекта пользователя."""
    email: Optional[str]
    smtp_user: Optional[str]  # опционально
    smtp_password: Optional[str]  # опционально
    from_email: Optional[str]  # опционально
    pk: object  # для логов




class SmtpEmailTransport:
    """Транспорт отправки через smtplib"""
    def __init__(self, config: SMTPConfig) -> None:
        self._cfg = config

    @staticmethod
    def _build_message(content: EmailContent) -> EmailMessage:
        msg = EmailMessage()
        msg["Subject"] = content.subject
        msg["From"] = content.from_email
        msg["To"] = ", ".join(content.to)
        if content.is_html:
            msg.add_alternative(content.body, subtype="html")
        else:
            msg.set_content(content.body)
        return msg

    def send(self, content: EmailContent) -> bool:
        msg = self._build_message(content)
        try:
            with smtplib.SMTP(self._cfg.host, self._cfg.port, timeout=self._cfg.timeout_sec) as srv:
                srv.ehlo()
                if self._cfg.use_tls:
                    srv.starttls()
                    srv.ehlo()

                # Логин обязателен только если указан пользователь
                if self._cfg.user:
                    srv.login(self._cfg.user, self._cfg.password or "")

                srv.send_message(msg)
            return True
        except Exception:
            logger.exception("SMTP ошибка при отправке на %s", content.to)
            return False


class DummyEmailTransport:
    """Заглушка для тестов/локалки — ничего не отправляет, всегда True."""
    def send(self, content: EmailContent) -> bool:  # type: ignore[override]
        logger.debug("DummyEmailTransport: %s", content)
        return True




class EmailSender:
   
    name = "email"

    def __init__(
        self,
        transport: Optional[EmailTransport] = None,
        base_config: Optional[SMTPConfig] = None,
    ) -> None:
        # Базовая конфигурация по умолчанию — из settings
        self._base_cfg = base_config or SMTPConfig()
        self._transport = transport or SmtpEmailTransport(self._base_cfg)

    @staticmethod
    def _normalize_recipients(to_emails: str | list[str]) -> list[str]:
        if isinstance(to_emails, str):
            return [to_emails]
        return list(to_emails)

    def deliver(
        self,
        user: UserWithEmail,
        message: str,
        subject: str = "Notification",
        html: bool = False,
    ) -> bool:
        """
        Готовит письмо и отправляет. Если у пользователя заданы `smtp_user/password`,
        они перекроют базовые из settings.
        """
        if not getattr(user, "email", None):
            return False

        # Сформировать итоговый from_email
        from_email = getattr(user, "from_email", None) or self._base_cfg.user or getattr(
            settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"
        )

        content = EmailContent(
            to=self._normalize_recipients(user.email),  # type: ignore[arg-type]
            subject=subject,
            body=message,
            from_email=from_email,
            is_html=html,
        )

        # Если у пользователя есть свои креды — временно создаём одноразовый транспорт с ними
        u_user = getattr(user, "smtp_user", None) or self._base_cfg.user
        u_pwd = getattr(user, "smtp_password", None) or self._base_cfg.password

        if u_user != self._base_cfg.user or u_pwd != self._base_cfg.password:
            # Создаём транспорт с переопределёнными кредами
            cfg = SMTPConfig(
                host=self._base_cfg.host,
                port=self._base_cfg.port,
                use_tls=self._base_cfg.use_tls,
                user=u_user,
                password=u_pwd,
                timeout_sec=self._base_cfg.timeout_sec,
            )
            transport = SmtpEmailTransport(cfg)
        else:
            transport = self._transport

        try:
            return bool(transport.send(content))
        except Exception:
            logger.exception("Ошибка в EmailSender.deliver для пользователя %s", getattr(user, "pk", user))
            return False


def send_email_via_smtp(
    to_emails: str | list[str],
    subject: str,
    body: str,
    from_email: Optional[str] = None,
    smtp_user: Optional[str] = None,
    smtp_password: Optional[str] = None,
    smtp_host: Optional[str] = None,
    smtp_port: Optional[int] = None,
    use_tls: Optional[bool] = None,
    html: bool = False,
) -> bool:
   
    base_cfg = SMTPConfig(
        host=smtp_host or getattr(settings, "SMTP_HOST", "smtp.gmail.com"),
        port=int(smtp_port or getattr(settings, "SMTP_PORT", 587)),
        use_tls=bool(getattr(settings, "SMTP_USE_TLS", True) if use_tls is None else use_tls),
        user=smtp_user or getattr(settings, "SMTP_DEFAULT_USER", "") or None,
        password=smtp_password or getattr(settings, "SMTP_DEFAULT_PASSWORD", "") or None,
    )

    sender = EmailSender(SmtpEmailTransport(base_cfg), base_cfg)

    class _TmpUser:
        email = to_emails
        smtp_user = base_cfg.user
        smtp_password = base_cfg.password
        from_email = from_email
        pk = "facade"

    return sender.deliver(_TmpUser(), message=body, subject=subject, html=html)
