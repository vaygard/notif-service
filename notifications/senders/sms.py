import logging

logger = logging.getLogger(__name__)


class SmsSender:
    name = "sms"

    def deliver(self, user: object, message: str) -> bool:
        phone = getattr(user, "phone", None)
        if not phone:
            return False
        # На данный момент не реалитзованно так как платный API
        logger.info("[SMS] to %s: %s", phone, message)
        return True