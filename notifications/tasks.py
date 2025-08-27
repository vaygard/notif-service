from __future__ import annotations

import logging

from celery import shared_task
from django.db import transaction

from .models import Notification
from .services import try_deliver

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def send_notification_task(self, notif_id: int) -> None:
    """Задача Celery: взять уведомление из БД и попытаться доставить.

    Если доставка не удалась — задача будет ретраиться.
    """
    with transaction.atomic():
        notif = Notification.objects.select_for_update().get(pk=notif_id)
        method = try_deliver(notif.user, notif.message)
        notif.attempts += 1

        if method:
            notif.delivered = True
            notif.delivery_method = method

        notif.save(update_fields=["delivered", "delivery_method", "attempts"])

        if not notif.delivered:
            logger.warning(
                "Notification %s not delivered, raising to trigger retry", notif_id
            )
            raise RuntimeError("Отправка не получилась, ретрай")

