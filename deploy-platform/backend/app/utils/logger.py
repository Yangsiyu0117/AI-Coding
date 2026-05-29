import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from app.config import settings

_fmt = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_access_fmt = logging.Formatter(
    "%(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def _file_handler(filename: str, max_mb: int, backups: int, fmt: logging.Formatter) -> RotatingFileHandler:
    os.makedirs(settings.log_dir, exist_ok=True)
    path = os.path.join(settings.log_dir, filename)
    h = RotatingFileHandler(path, maxBytes=max_mb * 1024 * 1024, backupCount=backups, encoding="utf-8")
    h.setFormatter(fmt)
    return h


def setup_logger(name: str = "deploy_platform") -> logging.Logger:
    logger = logging.getLogger(name)
    level = logging.DEBUG if settings.debug else logging.INFO
    logger.setLevel(level)

    if not logger.handlers:
        # Console (stdout → systemd journal)
        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(level)
        sh.setFormatter(_fmt)
        logger.addHandler(sh)

        # File (app.log, 10MB × 5)
        logger.addHandler(_file_handler("app.log", max_mb=10, backups=5, fmt=_fmt))

        # File (error.log, 10MB × 10) — only ERROR+
        eh = _file_handler("error.log", max_mb=10, backups=10, fmt=_fmt)
        eh.setLevel(logging.ERROR)
        logger.addHandler(eh)

    return logger


def setup_access_logger() -> logging.Logger:
    logger = logging.getLogger("deploy_access")
    logger.setLevel(logging.INFO)
    logger.propagate = False  # Don't duplicate to root logger

    if not logger.handlers:
        h = _file_handler("access.log", max_mb=10, backups=3, fmt=_access_fmt)
        h.setLevel(logging.INFO)
        logger.addHandler(h)

    return logger
