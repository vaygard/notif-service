from __future__ import annotations

from typing import Any

from django.contrib import messages
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.views.generic import TemplateView

from rest_framework import mixins, status, viewsets
from rest_framework.response import Response

from .models import Notification, User
from .serializers import (
    NotificationCreateSerializer,
    NotificationSerializer,
    UserSerializer,
)
from .tasks import send_notification_task  # используем задачу напрямую, чтобы избежать импорта отсутствующих сервисов


class UserViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """API для пользователей: создание и список."""
    queryset = User.objects.all().order_by("id")
    serializer_class = UserSerializer


class NotificationViewSet(viewsets.ViewSet):
    """API уведомлений: список и создание (асинхронная отправка)."""

    def list(self, request: HttpRequest) -> Response:
        qs = Notification.objects.select_related("user").order_by("-id")
        serializer = NotificationSerializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request: HttpRequest) -> Response:
        serializer = NotificationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        notif = Notification.objects.create(
            user_id=serializer.validated_data["user_id"],
            message=serializer.validated_data["message"].strip(),
        )
        send_notification_task.delay(notif.id)

        return Response(
            {"status": "queued", "id": notif.id},
            status=status.HTTP_202_ACCEPTED,
        )


class DemoView(TemplateView):
    """HTML-демо: список пользователей и уведомлений."""
    template_name = "notifications/demo.html"

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
        users = User.objects.order_by("-id")[:10]
        notifs = Notification.objects.select_related("user").order_by("-id")[:10]
        context = {"users": users, "notifs": notifs}
        return render(request, self.template_name, context)


def create_user_view(request: HttpRequest) -> Any:
    """Обработчик формы создания пользователя (POST)."""
    if request.method != "POST":
        return redirect("demo")

    email = request.POST.get("email") or None
    phone = request.POST.get("phone") or None
    tg = request.POST.get("telegram_id") or None

    if not any([email, phone, tg]):
        messages.error(
            request,
            "Укажите хотя бы один канал: email, phone или telegram_id.",
        )
        return redirect("demo")

    user = User.objects.create(email=email, phone=phone, telegram_id=tg)
    messages.success(request, f"Пользователь создан: id={user.id}")
    return redirect("demo")


def send_notification_view(request: HttpRequest) -> Any:
    """Обработчик формы отправки уведомления (POST)."""
    if request.method != "POST":
        return redirect("demo")

    try:
        user_id = int(request.POST.get("user_id"))
    except (TypeError, ValueError):
        messages.error(request, "Некорректный user_id.")
        return redirect("demo")

    message = (request.POST.get("message") or "").strip()
    if not message:
        messages.error(request, "Текст уведомления не может быть пустым.")
        return redirect("demo")

    if not User.objects.filter(id=user_id).exists():
        messages.error(request, f"Пользователь с id={user_id} не найден.")
        return redirect("demo")

    notif = Notification.objects.create(user_id=user_id, message=message)
    send_notification_task.delay(notif.id)
    messages.success(request, f"Уведомление поставлено в очередь (id={notif.id}).")
    return redirect("demo")