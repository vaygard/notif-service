# Вынесена логика отправки сообщений (email, SMS, Tg) в отдельный сервисный модуль.
import logging
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

def send_email(user, message) -> bool:
    '''
    отправка на email - при удачи true 

    '''
    if not user.email:
        return False
    send_mail("Notifications",message, None, [user.email])
    return True
def send_sms (user,message) ->bool:
    '''
    отправка на phone - при удачи true 
    В проде заменяется на реальный SDK/HTTP-запрос.
    '''
    if not user.phone:
        return False
    
    logger.info(f"[SMS] to {user.phone}: {message}")
    return True

def send_telegram(user, message) -> bool:
    """
    отправка на tg - при удачи true 
    В проде используется bot API/библиотеку.
    """
    if not user.telegram_id:
        return False
    logger.info(f"[TG] to {user.telegram_id}: {message}")
    return True
# очерёдность fallback: email -> sms -> telegram

DELIVERY_CHAIN = (("email", send_email), ("sms", send_sms), ("telegram", send_telegram))

# основная функция для перебора и возвращения успешного метода 
def try_deliver(user, message) -> str | None:
    for name, fn in DELIVERY_CHAIN:
        try:
            if fn(user, message):
                return name
        except Exception as e:
            logger.exception(f"Delivery error in {name}: {e}")
    return None
