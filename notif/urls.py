# Роутинг API: DRF-роутер для /api/users/ и ручная вьюха для /api/notifications/
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from notifications.views import UserViewSet, NotificationViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    # list/create для уведомлений
    path('api/notifications/', NotificationViewSet.as_view({'get': 'list', 'post': 'create'})),
]

from notifications.views import DemoView, create_user_view, send_notification_view

urlpatterns += [
    path("", DemoView.as_view(), name="demo"),                    # страница с формами
    path("demo/create-user/", create_user_view, name="create-user"),
    path("demo/send-notification/", send_notification_view, name="send-notification"),
]