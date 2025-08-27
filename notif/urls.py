from django.contrib import admin
from django.urls import path, include
from notifications import views as notifications_views

from notifications.views import DemoView, create_user_view, send_notification_view


urlpatterns = [
    path("admin/", admin.site.urls),
    
    path("", notifications_views.DemoView.as_view(), name="demo"),
    
    path("create-user/", notifications_views.create_user_view, name="create-user"),
    
    path("send/", notifications_views.send_notification_view, name="send_notification"),
    
    path('telegram/ping', notifications_views.telegram_ping_view, name='telegram-ping'),
   
]