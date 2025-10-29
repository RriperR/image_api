from __future__ import annotations

import logging
from aiohttp import web

from .config import get_settings
from .logging import setup_logging
from .errors import error_middleware
from .db import init_pg_pool, close_pg_pool
from .routes import routes


def create_app() -> web.Application:
    settings = get_settings()
    setup_logging(logging.INFO)

    app = web.Application(
        client_max_size=settings.CLIENT_MAX_SIZE_MB * 1024 ** 2,
        middlewares=[error_middleware],
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
