from django.db import models

class User (models.Model):
    """
    Может хранить три канала 
    Email - почта
    phone - номер телефона для SMS
    telegram_id - tg'ka
    """ 
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=12, blank=True, null=True)
    telegram_id = models.CharField(max_length=50, blank=True, null=True)

    #отображение в админ логах 
    def __str__(self):
        return self.email or self.phone or self.telegram_id or f'User#{self.pk}'

class Notification (models.Model):
    #ФАКТ ДОСТАВКИ СООБЩЕНИЯ
    '''
    - message - само сообщение 
    - delivered - доставилось ли сообщение 
    - delivered_method - способ доставки (email|sms|tg)
    - attempys - количество попыток 
    '''
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    delivered = models.BooleanField(default=False)
    delivery_method = models.CharField(max_length=20, blank=True, null=True) 
    attempts = models.PositiveIntegerField(default=0)
    


