import json
from pathlib import Path
from typing import Dict, List

_config_path = Path(__file__).resolve().parent.parent.parent / "service_types.json"
_cache: dict | None = None


def _load() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    with open(_config_path, "r", encoding="utf-8") as f:
        _cache = json.load(f)
    return _cache


def reload():
    global _cache
    _cache = None
    return _load()


def list_service_types() -> List[dict]:
    data = _load()
    return [
        {"name": name, "label": info["label"], "steps": info["steps"], "rollbackable": info.get("rollbackable", [])}
        for name, info in data.items()
    ]


def get_steps(type_name: str) -> List[str]:
    data = _load()
    if type_name not in data:
        raise ValueError(f"Unknown service type: {type_name}")
    return data[type_name]["steps"]


def get_rollbackable(type_name: str) -> set:
    data = _load()
    if type_name not in data:
        return set()
    return set(data[type_name].get("rollbackable", []))


def get_all_rollbackable() -> set:
    data = _load()
    result = set()
    for info in data.values():
        result.update(info.get("rollbackable", []))
    return result


STEP_LABELS: Dict[str, str] = {
    "precheck": "预检查",
    "backup": "备份",
    "upload": "上传",
    "copy": "复制更新",
    "verify": "完整性校验",
    "verify_version": "版本验证",
    "stop": "停止服务",
    "check_start": "启动服务",
    "log_check": "日志检查",
    "docker_scp": "镜像上传",
    "docker_load": "镜像加载",
    "docker_verify": "镜像校验",
    "switch_container": "容器切换",
    "container_check": "容器检查",
}

BUILTIN_TYPES = {"go", "docker"}


def _save_to_file(data: dict) -> None:
    with open(_config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    reload()


def save_service_type(name: str, info: dict) -> None:
    data = _load()
    data[name] = {
        "label": info["label"],
        "steps": info["steps"],
        "rollbackable": info.get("rollbackable", []),
    }
    _save_to_file(data)


def delete_service_type(name: str) -> None:
    data = _load()
    if name in data:
        del data[name]
    _save_to_file(data)
