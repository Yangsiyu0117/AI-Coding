import json
from pathlib import Path
from typing import Any

from app.config import settings

_config_path = Path(__file__).resolve().parent.parent.parent / "platform_settings.json"

_DEFAULTS = {
    "app_brand": settings.app_brand,
    "app_title": settings.app_title,
    "remote_update_base": settings.remote_update_base,
    "max_upload_size_mb": settings.max_upload_size_mb,
    "allowed_upload_extensions": settings.allowed_upload_extensions,
}


def load() -> dict:
    if not _config_path.exists():
        return dict(_DEFAULTS)
    with open(_config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    merged = dict(_DEFAULTS)
    merged.update(data)
    return merged


def get(key: str, default: Any = None) -> Any:
    data = load()
    return data.get(key, default)


def save(data: dict) -> None:
    current = load() if _config_path.exists() else {}
    current.update(data)
    # Remove keys that match defaults (keep file clean)
    clean = {k: v for k, v in current.items() if k in _DEFAULTS}
    with open(_config_path, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)
