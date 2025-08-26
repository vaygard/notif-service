@echo off
setlocal

rem Активируем venv
if not exist .\.venv\Scripts\activate.bat (
  python -m venv .venv
)
call .\.venv\Scripts\activate


set DJANGO_SETTINGS_MODULE=notif.settings

start "celery" cmd /k call .\.venv\Scripts\activate ^&^& set DJANGO_SETTINGS_MODULE=notif.settings^&^& celery -A notif.celery:app worker -l info -P solo

rem Поднимаем сервер Django
python manage.py runserver 0.0.0.0:8000

endlocal
