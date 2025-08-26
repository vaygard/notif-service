Param(
  [switch]$Pg,              # -Pg => PostgreSQL (по умолчанию SQLite)
  [int]$Port = 8000,        # порт dev-сервера
  [switch]$Open,            # -Open => открыть браузер
  [switch]$NoFixtures,      # -NoFixtures => не грузить fixtures
  [switch]$NoCelery,        # -NoCelery => не запускать воркер Celery
  [switch]$Eager,           # -Eager => выполнять Celery-задачи синхронно (без Redis/воркера)
  [string]$SuperuserUser,   # авто-создание суперпользователя: логин
  [string]$SuperuserEmail,  # email (опционально)
  [string]$SuperuserPass    # пароль
)

$ErrorActionPreference = "Stop"

# venv
if (-not (Test-Path .\.venv\Scripts\Activate.ps1)) {
  python -m venv .venv
}
.\.venv\Scripts\Activate.ps1

# зависимости
python -m pip install --upgrade pip | Out-Null
if (Test-Path .\requirements.txt) {
  pip install -r requirements.txt
}

# .env
if (-not (Test-Path .\.env)) {
  if (Test-Path .\.env.example) {
    Copy-Item .\.env.example .\.env
  } else {
@"
DEBUG=1
SECRET_KEY=dev-secret
ALLOWED_HOSTS=127.0.0.1,localhost
USE_SQLITE=1
DB_NAME=notif
DB_USER=notif
DB_PASSWORD=notif
DB_HOST=127.0.0.1
DB_PORT=5432
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
"@ | Set-Content -Encoding UTF8 .\.env
  }
}

# окружение
$env:DJANGO_SETTINGS_MODULE = "notif.settings"
$env:USE_SQLITE = $(if ($Pg) { "0" } else { "1" })
$env:CELERY_TASK_ALWAYS_EAGER = $(if ($Eager) { "1" } else { "0" })

# Redis-проверка (если async)
if (-not $Eager -and -not $NoCelery) {
  try {
    $tc = Test-NetConnection 127.0.0.1 -Port 6379 -WarningAction SilentlyContinue
    if (-not $tc.TcpTestSucceeded) {
      Write-Warning "Redis 127.0.0.1:6379 недоступен. Запусти redis-server или используй -Eager."
    }
  } catch { }
}

# миграции
python manage.py migrate

# fixtures
if (-not $NoFixtures) {
  if (Test-Path .\notifications\fixtures\demo.json) {
    try { python manage.py loaddata notifications/fixtures/demo.json | Out-Null } catch { }
  }
}


