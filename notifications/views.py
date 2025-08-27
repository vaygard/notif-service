from __future__ import annotations

from typing import Callable, Optional

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import TemplateView

from rest_framework import mixins, status, viewsets
from rest_framework.response import Response

from .models import Notification, User
from .serializers import (
    NotificationCreateSerializer,
    NotificationSerializer,
    UserSerializer,
)
from notifications.senders.telegram import send_telegram_message
from .tasks import send_notification_task


# Небольшая обёртка, чтобы можно было подменить отправку в тестах.
TelegramSenderFn = Callable[[str | int, str], bool]
_DEFAULT_TELEGRAM_SENDER: TelegramSenderFn = send_telegram_message


@require_GET
def telegram_ping_view(
    request: HttpRequest,
    sender: TelegramSenderFn = _DEFAULT_TELEGRAM_SENDER,
) -> HttpResponse:
    """
    Пинг бота: ?chat_id=12345&text=hello
    Возвращает "ok" или "failed" с соответствующим статусом.
    """
    chat_id = request.GET.get("chat_id")
    text = request.GET.get("text", "Telegram is wired")

    if not chat_id:
        return HttpResponse(
            "Передай ?chat_id=<число>",
            status=400,
            content_type="text/plain; charset=utf-8",
        )

    ok = sender(chat_id, text)
    body = "ok" if ok else "failed"
    code = 200 if ok else 500
    return HttpResponse(body, status=code, content_type="text/plain; charset=utf-8")


class UserViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """API для пользователей: создание и список."""
    queryset = User.objects.all().order_by("id")
    serializer_class = UserSerializer


class NotificationViewSet(viewsets.ViewSet):
    """API уведомлений: список и создание (асинхронная отправка через Celery)."""

    def list(self, request: HttpRequest) -> Response:
        qs = Notification.objects.select_related("user").order_by("-id")
        data = NotificationSerializer(qs, many=True).data
        return Response(data)

    def create(self, request: HttpRequest) -> Response:
        serializer = NotificationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = serializer.validated_data["message"].strip()
        notif = Notification.objects.create(
            user_id=serializer.validated_data["user_id"],
            message=message,
        )

        # ставим задачу на отправку
        send_notification_task.delay(notif.id)

        return Response({"status": "queued", "id": notif.id}, status=status.HTTP_202_ACCEPTED)


class DemoView(TemplateView):
    """HTML-демо: список пользователей и уведомлений."""
    template_name = "notifications/demo.html"

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context["users"] = User.objects.order_by("-id")[:10]
        context["notifs"] = Notification.objects.select_related("user").order_by("-id")[:10]
        return context


@require_POST
def create_user_view(request: HttpRequest) -> HttpResponse:
    """
    Обработчик формы создания пользователя.
    Ожидает поля: email, phone, telegram_id.
    """
    email = request.POST.get("email") or None
    phone = request.POST.get("phone") or None
    telegram_id = request.POST.get("telegram_id") or None

    if not (email or phone or telegram_id):
        messages.error(request, "Укажите хотя бы один канал: email, phone или telegram_id.")
        return redirect(reverse("demo"))

    user = User.objects.create(email=email, phone=phone, telegram_id=telegram_id)
    messages.success(request, f"Пользователь создан: id={user.id}")
    return redirect(reverse("demo"))


@require_POST
def send_notification_view(request: HttpRequest) -> HttpResponse:
    """
    Обработчик формы отправки уведомления.
    Ожидает: user_id, message (+ опционально smtp_user/smtp_password).
    """
    user_id_raw = request.POST.get("user_id")
    try:
        user_id = int(user_id_raw) if user_id_raw is not None else None
    except (TypeError, ValueError):
        user_id = None

    if not user_id:
        messages.error(request, "Некорректный user_id.")
        return redirect(reverse("demo"))

    message = (request.POST.get("message") or "").strip()
    if not message:
        messages.error(request, "Текст уведомления не может быть пустым.")
        return redirect(reverse("demo"))

    if not User.objects.filter(id=user_id).exists():
        messages.error(request, f"Пользователь с id={user_id} не найден.")
        return redirect(reverse("demo"))

    smtp_user: Optional[str] = (request.POST.get("smtp_user") or "").strip() or None
    smtp_password: Optional[str] = (request.POST.get("smtp_password") or "").strip() or None

    notif = Notification.objects.create(user_id=user_id, message=message)

    send_notification_task.delay(notif.id, smtp_user, smtp_password)

    messages.success(request, f"Уведомление поставлено в очередь (id={notif.id}).")
    return redirect(reverse("demo"))
