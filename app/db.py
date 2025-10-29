from __future__ import annotations

from aiohttp.web import Application
import asyncpg


async def init_pg_pool(app: Application) -> None:
    dsn: str = app["settings"].DATABASE_URL
    app["pg_pool"] = await asyncpg.create_pool(
        dsn=dsn,
        min_size=1,
        max_size=10,
        command_timeout=30,
    )


async def close_pg_pool(app: Application) -> None:
    pool = app.get("pg_pool")
    if pool:
        await pool.close()
