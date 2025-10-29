from __future__ import annotations

import json
import logging
from aiohttp import web

logger = logging.getLogger(__name__)


@web.middleware
async def error_middleware(request: web.Request, handler):
    try:
        return await handler(request)
    except web.HTTPException as http_exc:
        # Нормализуем тело в JSON
        if http_exc.content_type == "application/json":
            raise
        payload = {"detail": http_exc.reason or http_exc.text or http_exc.status}
        raise web.HTTPException(
            reason=http_exc.reason,
            body=json.dumps(payload),
            content_type="application/json",
            headers=http_exc.headers,
            status=http_exc.status,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unhandled error")
        payload = {"detail": "Internal Server Error"}
        return web.json_response(payload, status=500)
