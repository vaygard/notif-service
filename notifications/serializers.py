# Сериализаторы для валидации входных и выходных данных (что бы ручками не собирать словари)


from rest_framework import serializers
from .models import User, Notification

class UserSerializer(serializers.ModelSerializer):
    """ 
    CRUD по пользователям
    Автоматически превращает User в JSON и обратно
    """
    class Meta:
        model = User
        fields = ('id', 'email', 'phone', 'telegram_id')

# Проверяет, что в запросе есть user_id (целое число) и message (строка).
class NotificationCreateSerializer(serializers.Serializer):
    """Используется только для входных данных при создании уведомления"""
    user_id = serializers.IntegerField()
    message = serializers.CharField()
 #формат ответа (GET).    
class NotificationSerializer(serializers.ModelSerializer):
    """Это выходной сериализатор: берёт объект Notification и красиво возвращает его в JSON"""
    class Meta:
        model = Notification
        fields = ('id', 'user', 'message', 'delivered', 'delivery_method', 'attempts', 'created_at')
        
    