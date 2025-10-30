from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from contextvars import ContextVar


# request-scoped переменная с маршрутом
route_var: ContextVar[str] = ContextVar("route", default="-")


class RouteFilter(logging.Filter):
    """Добавляет поле %(route)s в запись."""
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.route = route_var.get()
        except Exception:
            record.route = "-"
        # Переименуем funcName -> functionName в формате — сам формат возьмёт %(functionName)s
        setattr(record, "functionName", getattr(record, "funcName", "-"))
        return True


def ensure_dir(path: str) -> None:
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def setup_logging_to_file(log_path: str, max_bytes: int, backups: int, level: int = logging.INFO) -> None:
    ensure_dir(log_path)

    fmt = "%(asctime)s,%(msecs)d: %(route)s: %(functionName)s: %(levelname)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    handler = RotatingFileHandler(log_path, maxBytes=max_bytes, backupCount=backups, encoding="utf-8")
    handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
    handler.addFilter(RouteFilter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    # Также дублируем в stdout (полезно в Docker)
    stream = logging.StreamHandler()
    stream.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
    stream.addFilter(RouteFilter())
    root.addHandler(stream)
