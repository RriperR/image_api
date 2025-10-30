# Image API (aiohttp + asyncpg + Pillow)

## Краткое описание

Асинхронный сервис для загрузки, конвертации и сжатия изображений. Сервис принимает популярные форматы (`jpeg`, `png`, `webp`, `bmp`, `gif` — берётся первый кадр), конвертирует в `JPEG`, опционально изменяет размер (`x`, `y`) и качество (`quality`), сохраняет результат в PostgreSQL и отдаёт по идентификатору.

> Проект упрощён, так как это тестовое задание. В конце перечислены возможные улучшения для продакшена.

---

## Стек

- Python 3.9
- aiohttp (async API)
- asyncpg (драйвер PostgreSQL)
- Pillow (обработка изображений)
- pydantic-settings (конфигурация)
- logging (ротация логов)
- Docker / docker-compose

---

## Структура проекта

```
image_api/
├─ app/
│  ├─ main.py               # точка входа
│  ├─ config.py             # конфигурация через pydantic-settings
│  ├─ db.py                 # пул соединений asyncpg
│  ├─ routes.py             # HTTP-маршруты
│  ├─ image_service.py      # конвертация/компрессия/resize (Pillow)
│  ├─ auth.py               # Bearer-token middleware
│  ├─ logging.py            # формат логов и хендлеры
│  ├─ middleware.py         # прокидка route в контекст логов
│  └─ errors.py             # JSON-мидлвар для ошибок
├─ init.sql                 # схема БД
├─ requirements.txt
├─ Dockerfile
├─ docker-compose.yml
├─ .env.example
├─ .env
└─ README.md
```

---

## Быстрый старт (Docker)

1) Подготовить `.env`:
```env
APP_HOST=0.0.0.0
APP_PORT=8080

DATABASE_URL=postgresql://app:app@db:5432/images_db
API_TOKENS=secret-token

CLIENT_MAX_SIZE_MB=20
MAX_IMAGE_MB=20
MAX_PIXELS=50000000
DEFAULT_QUALITY=85

LOG_PATH=./logs/app.log
LOG_MAX_BYTES=1048576
LOG_BACKUPS=5
```

2) Собрать и запустить:
```bash
docker compose build
docker compose up -d
```

3) Проверить работоспособность:
```bash
curl http://localhost:8080/health
# {"status":"ok"}
```

---

## Эндпоинты

### POST /images — загрузка и обработка изображения
- Авторизация: `Authorization: Bearer <token>`
- Тело: `multipart/form-data`
  - `file` — файл-изображение (обязательно)
  - `quality` — 1..95 (опционально; по умолчанию 85)
  - `x` — целевая ширина (опционально)
  - `y` — целевая высота (опционально)
- Поведение resize: изображение вписывается в рамку (`x`×`y`) без кропа, с сохранением пропорций.

Пример:
```bash
curl -X POST http://localhost:8080/images   -H "Authorization: Bearer secret-token"   -F "file=@./sample.png"   -F "quality=80"   -F "x=1280"   -F "y=720"
```

Ответ (201):
```json
{
  "id": "4fcc9986-facd-4e62-84b4-ddc8ebaca584",
  "width": 1280,
  "height": 720,
  "quality": 80,
  "size_bytes": 23391,
  "content_type": "image/jpeg",
  "source_format": "PNG",
  "filename": "sample.png"
}
```

### GET /images/{id} — получение изображения
- Авторизация: `Authorization: Bearer <token>`
- Ответ: `image/jpeg`

Пример:
```bash
curl -H "Authorization: Bearer secret-token" -o out.jpg http://localhost:8080/images/<uuid>
```

### GET /logs — чтение логов
- Авторизация: `Authorization: Bearer <token>`
- Параметры:
  - `limit` — количество последних строк (по умолчанию 200, максимум 10000)
- Ответ: `text/plain`

Пример:
```bash
curl -H "Authorization: Bearer secret-token"      "http://localhost:8080/logs?limit=200"
```

### GET /health — проверка состояния
- Открытый эндпоинт. Возвращает `{"status":"ok"}`.

---

## Схема БД

Таблица `images`:
| Поле          | Тип      | Описание                              |
|---------------|----------|----------------------------------------|
| id            | UUID     | идентификатор изображения              |
| filename      | text     | имя исходного файла                   |
| content_type  | text     | MIME-тип (всегда `image/jpeg`)        |
| data          | bytea    | бинарные данные JPEG                  |
| width         | int      | ширина                                 |
| height        | int      | высота                                 |
| quality       | int      | качество JPEG                          |
| size_bytes    | bigint   | размер в байтах                        |
| source_format | text     | формат исходника (например, PNG)       |
| created_at    | timestamptz | момент загрузки                    |

---

## Логирование

- Используется пакет `logging`.
- Формат логов:
  ```
  %(asctime)s,%(msecs)d: %(route)s: %(functionName)s: %(levelname)s: %(message)s
  ```
- Логи пишутся в `./logs/app.log` и дублируются в stdout.
- Ротация: `RotatingFileHandler` (`LOG_MAX_BYTES`, `LOG_BACKUPS`).

Пример строки лога:
```
2025-10-30 12:45:10,123: /images: upload_image: INFO: upload finished: width=800 height=600 quality=80 size=23391 source=PNG
```

---

## Авторизация

- Авторизация по Bearer-токену.
- Открыты только `/` и `/health`.
- Все остальные эндпоинты требуют заголовок:
  ```
  Authorization: Bearer <token>
  ```
- Список токенов настраивается через переменную окружения `API_TOKENS` (CSV или JSON).

---

## Ограничения и безопасность

- Ограничение размера запроса в aiohttp: `CLIENT_MAX_SIZE_MB`.
- Ограничение размера файла при чтении multipart: `MAX_IMAGE_MB`.
- Ограничение пикселей при декодировании: `MAX_PIXELS` (защита от decompression bomb).
- Конвертация в RGB и сохранение в JPEG с `optimize=True`, `progressive=True`.

---

## Упрощения (так как тестовое)

- Прямое сохранение бинарника изображения в PostgreSQL (колонка `bytea`).
- Отсутствие очередей/фоновой обработки.
- Простая авторизация по токену без ролей и без ротации ключей.
- Отсутствие отдельного каталога обработанных изображений.

---

## Возможные улучшения для продакшена

### Инфраструктура
- Использовать разные `.env`/секреты для БД и приложения (не хранить `environment` прямо в `docker-compose.yml`).
- Хранить секреты в Docker secrets / Vault.
- Использовать пакетный менеджер **uv** для быстрых и детерминированных сборок.
- Добавить Prometheus/Grafana/Loki (метрики, дешборды, логи).
- Добавить OpenTelemetry для трассировок.
- Настроить CI/CD (линтинг, тесты, сборка образов, сканирование уязвимостей).

### Хранение и данные
- Хранить в PostgreSQL только метаданные; загружать сами изображения в S3/MinIO/облачное хранилище.
- Добавить эндпоинт для отображения списка обработанных изображений и их метаданных (пагинация/фильтры).
- Добавить TTL/retention на старые объекты и Celery для фоновой очистки.

### Backend
- Добавить уровни доступа (роли), аудит (кто загрузил/читал).
- Реализовать строгие схемы запросов/ответов (pydantic-модели).
- Добавить ограничения по частоте запросов (rate limiting).
- Добавить тесты (unit + e2e) и нагрузочные сценарии.

### Безопасность
- Включить HTTPS (TLS) за реверс-прокси (nginx/traefik).
- Включить CORS по списку доверенных источников.
- Ротировать и отзывать токены, хранить их в безопасном хранилище.

