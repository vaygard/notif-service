from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import List, Optional

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


class Sender(ABC):
    """Базовый интерфейс для отправки сообщений."""
    name: str

    @abstractmethod
    def deliver(self, user: object, message: str) -> bool:
        """Попытаться доставить сообщение пользователю. Вернуть True при успехе."""
        raise NotImplementedError


class EmailSender(Sender):
    name = "email"

    def deliver(self, user: object, message: str) -> bool:
        email = getattr(user, "email", None)
        if not email:
            return False
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
        try:
            send_mail("Notification", message, from_email, [email])
            return True
        except Exception as exc:
            logger.exception("Ошибка при отправке email пользователю %s", getattr(user, "pk", repr(user)))
            # при необходимости можно логировать exc отдельно
            return False


class SmsSender(Sender):
    name = "sms"

    def deliver(self, user: object, message: str) -> bool:
        phone = getattr(user, "phone", None)
        if not phone:
            return False
        # Здесь заменить на реальный SDK/HTTP-клиент в проде
        logger.info("[SMS] to %s: %s", phone, message)
        return True


class TelegramSender(Sender):
    name = "telegram"

    def deliver(self, user: object, message: str) -> bool:
        tg_id = getattr(user, "telegram_id", None)
        if not tg_id:
            return False
        # В проде — использовать Bot API
        logger.info("[TG] to %s: %s", tg_id, message)
        return True


class DeliveryChainManager:
    """Попытка отправки по цепочке: возвращает имя первого успешного send'а или None."""
    def __init__(self, senders: List[Sender]) -> None:
        self.senders = list(senders)

    def try_deliver(self, user: object, message: str) -> Optional[str]:
        for sender in self.senders:
            try:
                if sender.deliver(user, message):
                    return sender.name
            except Exception:
                logger.exception("Ошибка доставки в %s", getattr(sender, "name", repr(sender)))
        return None


# По умолчанию: email -> sms -> telegram
DEFAULT_MANAGER: DeliveryChainManager = DeliveryChainManager(
    [EmailSender(), SmsSender(), TelegramSender()]
)


def try_deliver(user: object, message: str) -> Optional[str]:
    """Публичный API — возвращает имя способа доставки или None."""
    return DEFAULT_MANAGER.try_deliver(user, message)
