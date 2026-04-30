from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .config import LOGS_DIR, ensure_dirs
from .scanner import FileRecord


def make_trash_dir(media_base: str) -> str:
    base_parent = os.path.dirname(media_base)
    timestamp = datetime.now().strftime("clean_whatsapp_trash_%Y%m%d_%H%M%S")
    dst = os.path.join(base_parent, timestamp)
    os.makedirs(dst, exist_ok=True)
    try:
        Path(os.path.join(dst, ".nomedia")).touch(exist_ok=True)
    except Exception:
        pass
    return dst


def write_log(entries: List[Dict], cfg: Dict, moved_count: int, deleted_count: int, total_bytes: int, logs_dir: Path = LOGS_DIR) -> str:
    ensure_dirs(logs_dir=logs_dir)
    log_path = logs_dir / datetime.now().strftime("log_%Y%m%d_%H%M%S.json")
    meta = {
        "timestamp": datetime.now().isoformat(),
        "media_base": cfg["media_base"],
        "cfg": cfg,
        "summary": {
            "moved_count": moved_count,
            "deleted_count": deleted_count,
            "bytes_processed": total_bytes,
        },
    }
    with log_path.open("w", encoding="utf-8") as f:
        json.dump({"meta": meta, "entries": entries}, f, indent=2, ensure_ascii=False)
    return str(log_path)


def perform_actions(records: List[FileRecord], cfg: Dict, apply_moves: bool, apply_deletes: bool, logs_dir: Path = LOGS_DIR) -> Dict:
    actionable = [r for r in records if (r.action == "trash" and apply_moves) or (r.action == "delete" and apply_deletes)]
    result = {"log_path": "", "moved_count": 0, "deleted_count": 0, "bytes_processed": 0, "errors": []}
    if not actionable:
        return result

    trash_dir = None
    if apply_moves and any(r.action == "trash" for r in actionable):
        trash_dir = make_trash_dir(cfg["media_base"])

    log_entries = []
    for rec in actionable:
        if rec.action == "trash":
            assert trash_dir is not None
            dst = os.path.join(trash_dir, rec.rel_path)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            try:
                shutil.move(rec.src, dst)
                result["moved_count"] += 1
                result["bytes_processed"] += rec.size
                log_entries.append({"src": rec.src, "dst": dst, "planned_dst": dst, "action": "move", "size": rec.size, "mtime": rec.mtime, "error": None})
            except Exception as exc:
                result["errors"].append({"key": "move_failed", "path": rec.rel_path, "error": str(exc)})
                log_entries.append({"src": rec.src, "dst": None, "planned_dst": dst, "action": "move", "size": rec.size, "mtime": rec.mtime, "error": str(exc)})

        elif rec.action == "delete":
            try:
                os.remove(rec.src)
                result["deleted_count"] += 1
                result["bytes_processed"] += rec.size
                log_entries.append({"src": rec.src, "dst": None, "planned_dst": None, "action": "delete", "size": rec.size, "mtime": rec.mtime, "error": None})
            except Exception as exc:
                result["errors"].append({"key": "delete_failed", "path": rec.rel_path, "error": str(exc)})
                log_entries.append({"src": rec.src, "dst": None, "planned_dst": None, "action": "delete", "size": rec.size, "mtime": rec.mtime, "error": str(exc)})

    result["log_path"] = write_log(log_entries, cfg, result["moved_count"], result["deleted_count"], result["bytes_processed"], logs_dir)
    return result

