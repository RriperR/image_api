from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any, Optional

from aiohttp import web
from asyncpg import Pool, Record

from .image_service import process_to_jpeg, ImageProcessingError, new_image_id
from .validators import parse_optional_int, ValidationError


logger = logging.getLogger(__name__)
routes = web.RouteTableDef()


@routes.get("/health")
async def health(_request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


@routes.post("/images")
async def upload_image(request: web.Request) -> web.Response:
    """
    POST multipart/form-data:
      - file: обязательное
      - quality: [1..95], опционально
      - x, y: [1..20000], опционально
    """
    settings = request.app["settings"]
    pool: Pool = request.app["pg_pool"]

    # Читаем multipart построчно, чтобы держать контроль над размером файла
    reader = await request.multipart()

    file_bytes: Optional[bytes] = None
    filename: str = "upload"
    raw_quality: Optional[str] = None
    raw_x: Optional[str] = None
    raw_y: Optional[str] = None

    max_image_bytes = settings.MAX_IMAGE_MB * 1024 * 1024
    total_bytes = 0
    file_buf = bytearray()

    while True:
        part = await reader.next()
        if part is None:
            break

        if part.name == "file":
            if part.filename:
                filename = part.filename

            while True:
                chunk = await part.read_chunk(size=8192)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_image_bytes:
                    raise web.HTTPRequestEntityTooLarge(
                        reason=f"file exceeds limit {settings.MAX_IMAGE_MB} MB"
                    )
                file_buf.extend(chunk)

        elif part.name == "quality":
            raw_quality = await part.text()
        elif part.name == "x":
            raw_x = await part.text()
        elif part.name == "y":
            raw_y = await part.text()
        else:
            # Игнорируем неизвестные поля
            await part.release()

    if not file_buf:
        raise web.HTTPBadRequest(reason="file field is required")
    file_bytes = bytes(file_buf)

    try:
        quality = parse_optional_int("quality", raw_quality, min_value=1, max_value=95) or settings.DEFAULT_QUALITY
        target_w = parse_optional_int("x", raw_x, min_value=1, max_value=20000)
        target_h = parse_optional_int("y", raw_y, min_value=1, max_value=20000)
    except ValidationError as ve:
        raise web.HTTPBadRequest(reason=str(ve)) from ve

    try:
        jpeg_bytes, out_w, out_h, used_q, source_fmt = process_to_jpeg(
            file_bytes,
            quality=quality,
            target_w=target_w,
            target_h=target_h,
            max_pixels=settings.MAX_PIXELS,
        )
    except ImageProcessingError as ie:
        raise web.HTTPUnsupportedMediaType(reason=f"Invalid image: {ie}") from ie

    image_id: uuid.UUID = new_image_id()

    insert_sql = """
        INSERT INTO images (id, filename, content_type, data, width, height, quality, size_bytes, source_format)
        VALUES ($1, $2, 'image/jpeg', $3, $4, $5, $6, $7, $8)
    """

    async with pool.acquire() as conn:
        await conn.execute(
            insert_sql,
            image_id,
            filename,
            jpeg_bytes,
            out_w,
            out_h,
            used_q,
            len(jpeg_bytes),
            source_fmt,
        )

    payload: dict[str, Any] = {
        "id": str(image_id),
        "width": out_w,
        "height": out_h,
        "quality": used_q,
        "size_bytes": len(jpeg_bytes),
        "content_type": "image/jpeg",
        "source_format": source_fmt,
        "filename": filename,
    }
    return web.json_response(payload, status=201)


@routes.get("/images/{image_id}")
async def get_image(request: web.Request) -> web.StreamResponse:
    pool: Pool = request.app["pg_pool"]
    image_id_str = request.match_info["image_id"]

    try:
        image_id = uuid.UUID(image_id_str)
    except ValueError:
        raise web.HTTPBadRequest(reason="invalid UUID")

    sql = "SELECT data, content_type FROM images WHERE id = $1"
    async with pool.acquire() as conn:
        row: Record | None = await conn.fetchrow(sql, image_id)

    if row is None:
        raise web.HTTPNotFound(
            text=json.dumps({"detail": "Image not found"}),
            content_type="application/json",
        )

    data: bytes = row["data"]
    content_type: str = row["content_type"] or "image/jpeg"

    resp = web.Response(body=data, content_type=content_type)
    resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return resp


@routes.get("/logs")
async def read_logs(request: web.Request) -> web.StreamResponse:
    settings = request.app["settings"]
    limit_q = request.query.get("limit")
    try:
        limit = int(limit_q) if limit_q is not None else 200
        limit = max(1, min(limit, 10_000))
    except ValueError:
        raise web.HTTPBadRequest(reason="limit must be integer")

    log_path = settings.LOG_PATH
    if not os.path.exists(log_path):
        return web.Response(text="(no log file yet)\n", content_type="text/plain; charset=utf-8")

    # читаем последние N строк эффективно
    lines = _tail(log_path, limit)
    text = "".join(lines)
    return web.Response(text=text, content_type="text/plain; charset=utf-8")


def _tail(path: str, n: int) -> list[str]:
    # простая реализация tail -n с обратным чтением блоками
    size = os.path.getsize(path)
    block = 4096
    with open(path, "rb") as f:
        data = b""
        seek = 0
        while size + seek > 0 and data.count(b"\n") <= n:
            seek -= block
            f.seek(seek, os.SEEK_END)
            data = f.read(-seek) + data
            if -seek >= size:
                break
    lines = data.splitlines(keepends=True)[-n:]
    # декодируем как utf-8 с безопасной заменой
    return [line.decode("utf-8", errors="replace") for line in lines]
