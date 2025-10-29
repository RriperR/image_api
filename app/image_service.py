from __future__ import annotations

import uuid
from io import BytesIO
from typing import Optional, Tuple

from PIL import Image, ImageOps, UnidentifiedImageError, ImageFile


class ImageProcessingError(Exception):
    """Ошибка обработки изображения."""


def _coerce_rgb(img: Image.Image) -> Image.Image:
    if img.mode in ("RGB", "L"):
        return img.convert("RGB") if img.mode != "RGB" else img
    return img.convert("RGB")


def _compute_new_size(w: int, h: int, target_w: Optional[int], target_h: Optional[int]) -> Tuple[int, int]:
    if not target_w and not target_h:
        return w, h
    if target_w and target_h:
        scale = min(target_w / w, target_h / h)
        return max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    if target_w:
        scale = target_w / w
        return target_w, max(1, int(round(h * scale)))
    scale = target_h / h
    return max(1, int(round(w * scale))), target_h


def process_to_jpeg(
    file_bytes: bytes,
    *,
    quality: int,
    target_w: Optional[int],
    target_h: Optional[int],
    max_pixels: int,
) -> tuple[bytes, int, int, int, str]:
    """
    Возвращает: (jpeg_bytes, out_w, out_h, used_quality, source_format)
    """
    try:
        # Безопасно парсим крупные файлы
        Image.MAX_IMAGE_PIXELS = max_pixels
        ImageFile.LOAD_TRUNCATED_IMAGES = False

        with Image.open(BytesIO(file_bytes)) as img:
            source_format = (img.format or "UNKNOWN").upper()

            # EXIF-ориентация
            img = ImageOps.exif_transpose(img)

            out_w, out_h = _compute_new_size(img.width, img.height, target_w, target_h)
            if (out_w, out_h) != (img.width, img.height):
                img = img.resize((out_w, out_h), resample=Image.LANCZOS)

            img = _coerce_rgb(img)

            buf = BytesIO()
            q = max(1, min(95, int(quality)))
            img.save(buf, format="JPEG", quality=q, optimize=True, progressive=True)
            jpeg_bytes = buf.getvalue()
            return jpeg_bytes, img.width, img.height, q, source_format
    except UnidentifiedImageError as exc:
        raise ImageProcessingError("unsupported or corrupted image") from exc
    except Exception as exc:  # noqa: BLE001
        raise ImageProcessingError(str(exc)) from exc


def new_image_id() -> uuid.UUID:
    return uuid.uuid4()
