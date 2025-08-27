"""Сериализаторы для уведомлений и пользователей."""
from rest_framework import serializers

from .models import Notification, User


class UserSerializer(serializers.ModelSerializer):
    """CRUD по пользователям: превращает User в JSON и обратно."""

    class Meta:
        model = User
        fields = ("id", "email", "phone", "telegram_id")


class NotificationCreateSerializer(serializers.Serializer):
    """Сериализатор входных данных при создании уведомления."""

    user_id = serializers.IntegerField()
    message = serializers.CharField()


class NotificationSerializer(serializers.ModelSerializer):
    """Выходной сериализатор для объекта Notification."""

    class Meta:
        model = Notification
        fields = (
            "id",
            "user",
            "message",
            "delivered",
            "delivery_method",
            "attempts",
            "created_at",
        )

