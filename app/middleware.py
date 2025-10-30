from __future__ import annotations

from aiohttp import web
from .logging import route_var


@web.middleware
async def route_context_middleware(request: web.Request, handler):
    # Берём «человеческое» имя маршрута, иначе путь
    route = request.match_info.route.resource.canonical if request.match_info.route else request.path
    token = route_var.set(route)
    try:
        return await handler(request)
    finally:
        route_var.reset(token)
