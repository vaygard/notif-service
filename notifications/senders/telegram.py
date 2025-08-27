from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

import requests
from django.conf import settings

logger = logging.getLogger(__name__)



@dataclass(frozen=True)
class TelegramConfig:
    """
    Базовая конфигурация Telegram Bot API.
    Значения по умолчанию берутся из Django settings.
    """
    token: Optional[str] = (
        getattr(settings, "TELEGRAM_BOT_TOKEN", "") or None
    )
    base_url: str = "https://api.telegram.org"
    parse_mode: Optional[str] = (
        getattr(settings, "TELEGRAM_PARSE_MODE", "") or None
    )
    disable_web_page_preview: bool = bool(
        getattr(settings, "TELEGRAM_DISABLE_WPP", True)
    )
    timeout_sec: int = int(getattr(settings, "TELEGRAM_TIMEOUT", 10))


@dataclass(frozen=True)
class TelegramMessage:
    """Данные отправляемого сообщения."""
    chat_id: str
    text: str
    parse_mode: Optional[str] = None
    disable_web_page_preview: bool = True


@runtime_checkable
class TelegramTransport(Protocol):
    """Интерфейс транспорта отправки сообщений в Telegram."""
    def send(self, message: TelegramMessage) -> bool: ...


@runtime_checkable
class UserWithTelegram(Protocol):
    """Минимальные ожидания от объекта пользователя для Telegram-отправки."""
    telegram_id: Optional[str]
    telegram_bot_token: Optional[str]  # опционально
    pk: object  # для логов



class RequestsTelegramTransport:
    """
    Транспорт на базе requests.Session.
    """
    def __init__(
        self,
        config: TelegramConfig,
        session: Optional[requests.Session] = None,
    ) -> None:
        self._cfg = config
        self._session = session or requests.Session()

    def _make_url(self) -> str:
        if not self._cfg.token:
            raise ValueError("TELEGRAM_BOT_TOKEN не задан")
        return f"{self._cfg.base_url}/bot{self._cfg.token}/sendMessage"

    def send(self, message: TelegramMessage) -> bool:
        url = self._make_url()
        payload = {
            "chat_id": message.chat_id,
            "text": message.text,
            "disable_web_page_preview": message.disable_web_page_preview,
        }
        if message.parse_mode:
            payload["parse_mode"] = message.parse_mode

        try:
            resp = self._session.post(url, json=payload, timeout=self._cfg.timeout_sec)
            if resp.status_code != 200:
                logger.error("Telegram HTTP %s: %s", resp.status_code, resp.text)
                return False

            data = resp.json()
            if not data.get("ok", False):
                logger.error(
                    "Telegram API error: code=%s desc=%s",
                    data.get("error_code"),
                    data.get("description"),
                )
                return False
            return True
        except requests.RequestException:
            logger.exception("Ошибка сети при отправке в Telegram")
            return False
        except Exception:
            logger.exception("Непредвиденная ошибка при отправке в Telegram")
            return False


class DummyTelegramTransport:
    """Заглушка для тестов/локальной разработки — всегда True."""
    def send(self, message: TelegramMessage) -> bool:  # type: ignore[override]
        logger.debug("DummyTelegramTransport: %s", message)
        return True



class TelegramSender:
    """
    Сервис отправки сообщений в Telegram.
    """
    name = "telegram"
    priority = 30

    def __init__(
        self,
        transport: Optional[TelegramTransport] = None,
        base_config: Optional[TelegramConfig] = None,
    ) -> None:
        self._base_cfg = base_config or TelegramConfig()
        self._transport = transport or RequestsTelegramTransport(self._base_cfg)

    @staticmethod
    def _normalize_chat_id(chat_id: str | int) -> str:
        return str(chat_id)

    def deliver(
        self,
        user: UserWithTelegram,
        message: str,
        *,
        parse_mode: Optional[str] = None,
        disable_web_page_preview: Optional[bool] = None,
    ) -> bool:
        """
        Отправляет сообщение пользователю.
        Если у пользователя задан персональный токен, он перекроет базовый.
        """
        chat_id = getattr(user, "telegram_id", None)
        if not chat_id:
            return False

        # Итоговые параметры
        pmode = (
            parse_mode
            if parse_mode is not None
            else self._base_cfg.parse_mode
        )
        disable_wpp = (
            self._base_cfg.disable_web_page_preview
            if disable_web_page_preview is None
            else bool(disable_web_page_preview)
        )

        msg = TelegramMessage(
            chat_id=self._normalize_chat_id(chat_id),
            text=message,
            parse_mode=pmode,
            disable_web_page_preview=disable_wpp,
        )

        # При необходимости создаём одноразовый транспорт с персональным токеном
        user_token = getattr(user, "telegram_bot_token", None)
        if user_token and user_token != self._base_cfg.token:
            cfg = TelegramConfig(
                token=user_token,
                base_url=self._base_cfg.base_url,
                parse_mode=self._base_cfg.parse_mode,
                disable_web_page_preview=self._base_cfg.disable_web_page_preview,
                timeout_sec=self._base_cfg.timeout_sec,
            )
            transport = RequestsTelegramTransport(cfg)
        else:
            transport = self._transport

        try:
            ok = bool(transport.send(msg))
            if not ok:
                logger.warning("Telegram send to %s вернул False", chat_id)
            return ok
        except Exception:
            logger.exception(
                "Ошибка в TelegramSender.deliver для пользователя %s",
                getattr(user, "pk", user),
            )
            return False



def send_telegram_message(
    chat_id: str | int,
    text: str,
    *,
    token: Optional[str] = None,
    parse_mode: Optional[str] = None,
    disable_web_page_preview: bool = True,
    timeout: int = 10,
) -> bool:
   
    base_cfg = TelegramConfig(
        token=token or getattr(settings, "TELEGRAM_BOT_TOKEN", "") or None,
        base_url="https://api.telegram.org",
        parse_mode=(
            parse_mode
            if parse_mode is not None
            else getattr(settings, "TELEGRAM_PARSE_MODE", "") or None
        ),
        disable_web_page_preview=disable_web_page_preview,
        timeout_sec=timeout,
    )

    sender = TelegramSender(
        transport=RequestsTelegramTransport(base_cfg),
        base_config=base_cfg,
    )

    class _TmpUser:
        telegram_id = chat_id
        telegram_bot_token = base_cfg.token
        pk = "facade"

    return sender.deliver(_TmpUser(), message=text)
