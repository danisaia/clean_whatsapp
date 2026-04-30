from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

from .config import LOGS_DIR


def list_available_logs(logs_dir: Path = LOGS_DIR) -> List[str]:
    try:
        files = [str(logs_dir / name) for name in os.listdir(logs_dir) if name.endswith(".json")]
    except FileNotFoundError:
        return []
    return sorted(files, reverse=True)


def preview_restore_from_log(log_path: str) -> Tuple[List[Dict], List[Dict]]:
    with open(log_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    restorable = []
    skipped = []
    for entry in data.get("entries", []):
        reason_key = None
        if entry.get("error"):
            reason_key = "restore_reason_error"
        if entry.get("action") != "move":
            reason_key = reason_key or "restore_reason_deleted"

        actual_src = entry.get("dst") or entry.get("planned_dst")
        restore_to = entry.get("src")
        if not actual_src or not restore_to:
            reason_key = reason_key or "restore_reason_incomplete"
        elif not os.path.exists(actual_src):
            reason_key = reason_key or "restore_reason_missing"

        if reason_key:
            skipped.append({"entry": entry, "reason_key": reason_key})
        else:
            restorable.append({"entry": entry, "current_location": actual_src, "restore_to": restore_to})
    return restorable, skipped


def restore_entries(restorable: List[Dict]) -> Dict:
    result = {"restored_count": 0, "errors": []}
    for item in restorable:
        src = item["current_location"]
        dst = item["restore_to"]
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            shutil.move(src, dst)
            result["restored_count"] += 1
        except Exception as exc:
            result["errors"].append({"path": dst, "error": str(exc)})
    return result

