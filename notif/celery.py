import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'notif.settings')  

app = Celery('notif')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
