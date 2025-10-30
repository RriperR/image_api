from __future__ import annotations

from aiohttp import web
import logging

from .config import get_settings
from .logging import setup_logging_to_file
from .errors import error_middleware
from .middleware import route_context_middleware
from .auth import bearer_auth_middleware
from .db import init_pg_pool, close_pg_pool
from .routes import routes


def create_app() -> web.Application:
    settings = get_settings()

    # Логирование в файл + stdout с нужным форматом
    setup_logging_to_file(
        log_path=settings.LOG_PATH,
        max_bytes=settings.LOG_MAX_BYTES,
        backups=settings.LOG_BACKUPS,
        level=logging.INFO,
    )

    app = web.Application(
        client_max_size=settings.CLIENT_MAX_SIZE_MB * 1024 ** 2,
        middlewares=[
            route_context_middleware,
            bearer_auth_middleware,
            error_middleware,
        ],
    )
    app["settings"] = settings
    app.router.add_routes(routes)

    app.on_startup.append(init_pg_pool)
    app.on_cleanup.append(close_pg_pool)
    return app


def main() -> None:
    app = create_app()
    s = app["settings"]
    web.run_app(app, host=s.APP_HOST, port=s.APP_PORT)


if __name__ == "__main__":
    main()
