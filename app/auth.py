from __future__ import annotations

from aiohttp import web


OPEN_ROUTES = {
    ("GET", "/"),
    ("GET", "/health"),
    ("GET", "/favicon.ico"),
}


def _is_open(request: web.Request) -> bool:
    method = request.method.upper()
    # canonical без параметров пути
    path = request.match_info.route.resource.canonical if request.match_info.route else request.path
    return (method, path) in OPEN_ROUTES


@web.middleware
async def bearer_auth_middleware(request: web.Request, handler):
    if _is_open(request):
        return await handler(request)

    settings = request.app["settings"]
    # Ничего не настроено — запретим всё кроме OPEN_ROUTES
    valid_tokens = set(settings.API_TOKENS or [])

    auth_header = request.headers.get("Authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token or token not in valid_tokens:
        raise web.HTTPUnauthorized(
            reason="Missing or invalid bearer token",
            headers={"WWW-Authenticate": 'Bearer realm="image-api"'},
        )

    return await handler(request)
