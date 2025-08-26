from rest_framework import viewsets, mixins, status
from rest_framework.response import Response

# Django для демо-страницы 
from django.views.generic import TemplateView
from django.shortcuts import render, redirect
from django.contrib import messages

#   модели
from .models import User, Notification
from .serializers import UserSerializer, NotificationCreateSerializer, NotificationSerializer
from .tasks import send_notification_task


#  REST API (DRF)

class UserViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    POST /api/users/  — создать пользователя
    GET  /api/users/  — список пользователей
    """
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer


class NotificationViewSet(viewsets.ViewSet):
    """
    GET  /api/notifications/ — список уведомлений
    POST /api/notifications/ — создать уведомление и отправить его асинхронно (Celery)
    """
    def list(self, request):
        qs = Notification.objects.select_related('user').order_by('-id')
        return Response(NotificationSerializer(qs, many=True).data)

    def create(self, request):
        ser = NotificationCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        notif = Notification.objects.create(
            user_id=ser.validated_data['user_id'],
            message=ser.validated_data['message']
        )
        # Асинхронная отправка
        send_notification_task.delay(notif.id)
        return Response({'status': 'queued', 'id': notif.id}, status=status.HTTP_202_ACCEPTED)


#  ВИЗУАЛ 

class DemoView(TemplateView):
    """
   HTML - форма
    """
    template_name = "notifications/demo.html"

    def get(self, request, *args, **kwargs):
        users = User.objects.order_by('-id')[:10]
        notifs = Notification.objects.select_related('user').order_by('-id')[:10]
        return render(request, self.template_name, {
            'users': users,
            'notifs': notifs,
        })


def create_user_view(request):
    """
    POST /demo/create-user/ — обработчик формы создания пользователя.
    """
    if request.method == "POST":
        email = request.POST.get("email") or None
        phone = request.POST.get("phone") or None
        tg = request.POST.get("telegram_id") or None

        if not any([email, phone, tg]):
            messages.error(request, "Укажите хотя бы один канал: email, phone или telegram_id.")
            return redirect("demo")

        user = User.objects.create(email=email, phone=phone, telegram_id=tg)
        messages.success(request, f"Пользователь создан: id={user.id}")
        return redirect("demo")

    return redirect("demo")


def send_notification_view(request):
    """
    POST /demo/send-notification/ — обработчик формы отправки уведомления.
    """
    if request.method == "POST":
        # Валидация user_id
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

    return redirect("demo")