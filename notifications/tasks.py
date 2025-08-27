from __future__ import annotations

import logging
from typing import Optional

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
def send_notification_task(
    self,
    notif_id: int,
    smtp_user: Optional[str] = None,
    smtp_password: Optional[str] = None,) -> None:
 
    with transaction.atomic():
        notif = Notification.objects.select_for_update().get(pk=notif_id)

        user = notif.user
        if smtp_user:
            user.smtp_user = smtp_user
        if smtp_password:
            user.smtp_password = smtp_password

        method = try_deliver(user, notif.message)
        notif.attempts += 1

        if method:
            notif.delivered = True
            notif.delivery_method = method

        notif.save(
            update_fields=["delivered", "delivery_method", "attempts"],
        )

        if not notif.delivered:
            logger.warning(
                "Notification %s not delivered; triggering retry", notif_id
            )
            raise RuntimeError("Отправка не получилась, ретрай")

