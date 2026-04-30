from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from .config import KNOWN_MEDIA_BASES


EXTENSION_MAP = {
    "images": {"jpg", "jpeg", "png", "webp", "heic"},
    "animated_gifs": {"gif"},
    "video": {"mp4", "mkv", "mov", "3gp", "avi"},
    "audio": {"mp3", "m4a", "opus", "ogg", "amr"},
    "voice": {"opus", "m4a", "amr"},
    "stickers": {"webp"},
    "profile": {"jpg", "jpeg", "png", "webp"},
}

GLOBAL_MEDIA_EXTS = set().union(*EXTENSION_MAP.values())
EXCLUDE_NAMES = {".nomedia", "desktop.ini", "thumbs.db"}
ACTION_KEYS = ("keep", "trash", "delete")
MEDIA_FILTER_GROUPS = {
    "include_images": {"images", "animated_gifs", "profile"},
    "include_videos": {"video"},
    "include_audio": {"audio", "voice"},
    "include_stickers": {"stickers"},
}


@dataclass
class FileRecord:
    src: str
    rel_path: str
    size: int
    mtime: float
    age_days: int
    action: str
    media_type: str


def normalize_text(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def detect_media_base(current: str | None = None) -> str:
    if current and os.path.exists(current):
        return current
    for path in KNOWN_MEDIA_BASES:
        if os.path.exists(path):
            return path
    return current or KNOWN_MEDIA_BASES[0]


def check_storage_access(media_base: str) -> Tuple[bool, str, Dict]:
    if not os.path.exists(media_base):
        return False, "folder_missing", {"media_base": media_base}
    try:
        os.listdir(media_base)
    except PermissionError:
        return False, "permission_denied", {}
    except Exception as exc:
        return False, "folder_error", {"error": exc}
    return True, "ok", {}


def get_relative_path(path: str, base: str) -> str:
    try:
        return str(Path(path).relative_to(Path(base)))
    except ValueError:
        return os.path.relpath(path, base)


def detect_media_type(parts: List[str], ext: str) -> str | None:
    normalized_parts = [normalize_text(part) for part in parts]
    for key, allowed_exts in EXTENSION_MAP.items():
        normalized_key = normalize_text(key)
        if any(normalized_key in part for part in normalized_parts):
            return key if ext in allowed_exts else None
    return "other" if ext in GLOBAL_MEDIA_EXTS else None


def action_for_age(age_days: int, cfg: Dict) -> str:
    keep_d = int(cfg["age_keep_days"])
    trash_min = int(cfg["age_trash_min"])
    trash_max = int(cfg["age_trash_max"])
    if age_days <= keep_d:
        return "keep"
    if trash_min <= age_days <= trash_max:
        return "trash"
    return "delete"


def media_type_enabled(media_type: str, cfg: Dict) -> bool:
    for flag, media_types in MEDIA_FILTER_GROUPS.items():
        if media_type in media_types:
            return bool(cfg.get(flag, True))
    return True


def scan_files(media_base: str, cfg: Dict) -> Tuple[List[FileRecord], Dict]:
    now = time.time()
    records: List[FileRecord] = []
    summary = {
        "total_files": 0,
        "total_size": 0,
        "ignored_files": 0,
        "permission_errors": 0,
        "by_action": {key: {"count": 0, "size": 0} for key in ACTION_KEYS},
        "by_media": {},
    }

    for root, dirs, files in os.walk(media_base):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for filename in files:
            path = os.path.join(root, filename)
            name = filename.lower()
            if name in EXCLUDE_NAMES or name.startswith("."):
                summary["ignored_files"] += 1
                continue

            try:
                stat = os.stat(path)
            except FileNotFoundError:
                continue
            except PermissionError:
                summary["permission_errors"] += 1
                continue

            rel_path = get_relative_path(path, media_base)
            parts = [part.lower() for part in Path(rel_path).parts]
            ext = Path(filename).suffix.lower().lstrip(".")
            media_type = detect_media_type(parts, ext)
            if media_type is None:
                summary["ignored_files"] += 1
                continue
            if not media_type_enabled(media_type, cfg):
                summary["ignored_files"] += 1
                continue

            if not cfg.get("include_private", False) and "private" in parts:
                summary["ignored_files"] += 1
                continue
            if not cfg.get("include_sent", True) and "sent" in parts:
                summary["ignored_files"] += 1
                continue

            age_days = int((now - stat.st_mtime) / 86400)
            action = action_for_age(age_days, cfg)
            record = FileRecord(
                src=path,
                rel_path=rel_path,
                size=stat.st_size,
                mtime=stat.st_mtime,
                age_days=age_days,
                action=action,
                media_type=media_type,
            )
            records.append(record)

            summary["total_files"] += 1
            summary["total_size"] += stat.st_size
            summary["by_action"][action]["count"] += 1
            summary["by_action"][action]["size"] += stat.st_size
            media_bucket = summary["by_media"].setdefault(media_type, {"count": 0, "size": 0})
            media_bucket["count"] += 1
            media_bucket["size"] += stat.st_size

    return records, summary
