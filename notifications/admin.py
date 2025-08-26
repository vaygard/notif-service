#регистрацйия моделий 
from django.contrib import admin
from .models import User, Notification

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'phone', 'telegram_id')
    search_fields = ('email', 'phone', 'telegram_id')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):  
    list_display = ('id', 'user', 'delivered', 'delivery_method', 'attempts', 'created_at')
    list_filter = ('delivered', 'delivery_method')  
    search_fields = ('message',)

