
# Система уведомлений (Email → SMS → Telegram с fallback)
## !!Тестовое задание!!
Мини-сервис на Django + DRF + Celery + Redis. Отправляет уведомления пользователям по цепочке: сначала Email, затем SMS, затем Telegram. Если канал недоступен, пробует следующий. Есть простая HTML-страница для ручной проверки, REST API и скрипты запуска для Windows.

## Стек
- Python 3.10+
- Django 3.2 (LTS), DRF
- Celery 5, Redis (как брокер и backend результатов)
- PostgreSQL (опционально; по умолчанию SQLite)
- cacheops (точечное кеширование)
- (опционально) drf-spectacular для Swagger UI
## Возможности

- Асинхронная отправка через Celery/Redis.
    
- Надёжная доставка с fallback: email → sms → telegram.
    
- Простая демо-страница `/` для кликового теста.
    
- REST API: создание пользователя и постановка уведомления в очередь.
    
- Конфигурация через `.env`. Быстрый dev-режим без Redis (eager).
## Быстрый старт (Windows, PowerShell)
1) Клонирование и переход в папку проекта
git clone <repo-url>
cd <repo-folder>
	
1) Запуск «всё-в-одном»
по умолчанию: SQLite, загрузка фикстуры, Celery-воркер и runserver
 .\run.ps1 -Open
Откроется `http://127.0.0.1:8000/` — демо-страница с формами:
2. создать пользователя,
3. отправить уведомление.
Если нужно «без Redis/воркера», для локального теста:
.\run.ps1 -Eager -Open
В этом режиме Celery-задачи выполняются синхронно в том же процессе.
Остановка процессов:
.\stop.ps1
Ручной запуск
 venv
python -m venv .venv
	.\.venv\Scripts\Activate.ps1
	python -m pip install --upgrade pip
	pip install -r requirements.txt
	
 .env
	copy .env.example .env    # отредактируйте при необходимости

4. миграции и (опц.) фикстуры
 миграции и (опц.) фикстуры
python manage.py migrate
python manage.py loaddata notifications/fixtures/demo.json
	
5. вариант A: dev без Redis (синхронно)
 вариант A: dev без Redis (синхронно)
в .env: CELERY_TASK_ALWAYS_EAGER=1
python manage.py runserver
	
6. вариант B: асинхронно с Redis
 вариант B: асинхронно с Redis
в .env: CELERY_TASK_ALWAYS_EAGER=0, REDIS_URL=redis://127.0.0.1:6379/0
redis-server   # или убедитесь, что сервис Redis запущен
python manage.py runserver
