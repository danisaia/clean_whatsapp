from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List


KNOWN_MEDIA_BASES = [
    "/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Media",
    "/storage/emulated/0/Android/media/com.whatsapp.w4b/WhatsApp Business/Media",
    "/storage/emulated/0/WhatsApp/Media",
]

CONFIG_PATH = Path(os.path.expanduser("~/.config/clean-whatsapp/config.json"))
LOGS_DIR = Path(os.path.expanduser("~/.local/share/clean-whatsapp/logs"))

DEFAULTS = {
    "language": None,
    "media_base": KNOWN_MEDIA_BASES[0],
    "age_keep_days": 60,
    "age_trash_min": 61,
    "age_trash_max": 180,
    "include_private": False,
    "include_sent": True,
    "include_images": True,
    "include_videos": True,
    "include_audio": True,
    "include_stickers": True,
    "show_top_files": 10,
    "setup_complete": False,
}


def ensure_dirs(config_path: Path = CONFIG_PATH, logs_dir: Path = LOGS_DIR) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)


def normalize_config(cfg: Dict) -> Dict:
    normalized = dict(DEFAULTS)
    normalized.update(cfg or {})

    for key in ("age_keep_days", "age_trash_min", "age_trash_max", "show_top_files"):
        try:
            normalized[key] = int(normalized[key])
        except (TypeError, ValueError):
            normalized[key] = DEFAULTS[key]

    normalized["include_private"] = bool(normalized.get("include_private"))
    normalized["include_sent"] = bool(normalized.get("include_sent"))
    normalized["include_images"] = bool(normalized.get("include_images"))
    normalized["include_videos"] = bool(normalized.get("include_videos"))
    normalized["include_audio"] = bool(normalized.get("include_audio"))
    normalized["include_stickers"] = bool(normalized.get("include_stickers"))
    normalized["setup_complete"] = bool(normalized.get("setup_complete"))
    if not isinstance(normalized.get("media_base"), str):
        normalized["media_base"] = DEFAULTS["media_base"]
    if normalized.get("language") not in {"en", "pt", "es", "fr", None}:
        normalized["language"] = None
    return normalized


def validate_config(cfg: Dict) -> List[str]:
    errors = []
    if not str(cfg.get("media_base", "")).strip():
        errors.append("config_error_media_base")
    if cfg.get("age_keep_days", 0) < 0:
        errors.append("config_error_keep_days")
    if not (cfg.get("age_keep_days", 0) < cfg.get("age_trash_min", 0) <= cfg.get("age_trash_max", 0)):
        errors.append("config_error_age_order")
    if cfg.get("show_top_files", 1) < 1:
        errors.append("config_error_top_files")
    return errors


def load_config(config_path: Path = CONFIG_PATH) -> Dict:
    try:
        with config_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    return normalize_config(data)


def save_config(cfg: Dict, config_path: Path = CONFIG_PATH, logs_dir: Path = LOGS_DIR) -> None:
    ensure_dirs(config_path, logs_dir)
    data = {k: v for k, v in normalize_config(cfg).items() if not k.startswith("_")}
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
