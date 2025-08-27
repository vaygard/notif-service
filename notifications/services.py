from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Iterable, List, Optional, Sequence

logger = logging.getLogger(__name__)


class Sender(ABC):
    """
    Базовый интерфейс транспорта доставки.
    Реализации должны задать уникальное имя и опциональный приоритет.
    """
    name: str = "sender"
    priority: int = 100  # ниже — выше в цепочке

    @abstractmethod
    def deliver(self, user: object, message: str) -> bool:
        """Пытается доставить сообщение. True при успехе, иначе False."""
        raise NotImplementedError


class DeliveryChainManager:
    """
    Идёт по цепочке отправщиков (в порядке приоритета) и пытается доставить.
    Возвращает имя первого успешного отправщика или None.
    """

    def __init__(self, senders: Iterable[Sender]) -> None:
        self._senders: List[Sender] = sorted(
            list(senders),
            key=lambda s: getattr(s, "priority", 100),
        )

    @property
    def senders(self) -> Sequence[Sender]:
        return tuple(self._senders)

    def try_deliver(self, user: object, message: str) -> Optional[str]:
        for sender in self._senders:
            try:
                if sender.deliver(user, message):
                    return sender.name
            except Exception:
                logger.exception(
                    "Ошибка доставки в %s",
                    getattr(sender, "name", sender.__class__.__name__),
                )
        return None

    def add_sender(self, sender: Sender) -> None:
        """Позволяет динамически расширять цепочку (например, в тестах)."""
        self._senders.append(sender)
        self._senders.sort(key=lambda s: getattr(s, "priority", 100))


_manager: Optional[DeliveryChainManager] = None


def get_default_manager() -> DeliveryChainManager:
    """
    Email ставим раньше Telegram, но это можно переопределить через приоритеты.
    """
    global _manager
    if _manager is None:
        from .senders.email import EmailSender
        from .senders.telegram import TelegramSender

        # можно подключить SMS, Push и т.д., просто добавив сюда
        _manager = DeliveryChainManager(
            [
                EmailSender(),     # priority по умолчанию у классов отправки
                TelegramSender(),
            ]
        )
    return _manager


def try_deliver(user: object, message: str) -> Optional[str]:
    """
    Удобный фасад: попробует доставить через стандартный менеджер
    и вернёт имя канала-успешника или None.
    """
    return get_default_manager().try_deliver(user, message)
