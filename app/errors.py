from __future__ import annotations

import logging

from aiohttp import web

logger = logging.getLogger(__name__)


@web.middleware
async def error_middleware(request: web.Request, handler):
    try:
        return await handler(request)
    except web.HTTPException as http_exc:
        # Если уже application/json — пропускаем как есть
        if (http_exc.content_type or "").lower() == "application/json":
            raise

        # Снимем конфликтующий Content-Type из оригинальных заголовков
        headers = {}
        if http_exc.headers:
            headers = {k: v for k, v in http_exc.headers.items() if k.lower() != "content-type"}

        payload = {
            "detail": (http_exc.reason or http_exc.text or http_exc.status)
        }

        # Отдаём нормализованный JSON c оригинальным статусом и (безопасными) заголовками
        return web.json_response(payload, status=http_exc.status, headers=headers)

    except Exception:  # noqa: BLE001
        logger.exception("Unhandled error")
        return web.json_response({"detail": "Internal Server Error"}, status=500)