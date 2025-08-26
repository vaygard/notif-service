
from celery import shared_task
from django.db import transaction
from .models import Notification
from .services import try_deliver

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_notification_task(self, notif_id: int):
  """
  celery 
  -берет уведобление из БД
  -траит их доставить 
  - если не получается ретраит
  """
  with transaction.atomic():
    notif = Notification.objects.select_for_update().get(id=notif_id)
    method = try_deliver(notif.user, notif.message)
    notif.attempts += 1
    if method:
      notif.delivered = True
      notif.delivery_method = method
    notif.save(update_fields=["delivered", "delivery_method", "attempts"])

    # если не получилось ретраим 
    if not notif.delivered:
      raise RuntimeError ("Отправка не получилась, ретрай") 
    
