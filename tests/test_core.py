from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from clean_whatsapp_app.actions import perform_actions
from clean_whatsapp_app.config import DEFAULTS, normalize_config, validate_config
from clean_whatsapp_app.i18n import LANGUAGES, locale_key_sets
from clean_whatsapp_app.restore import preview_restore_from_log
from clean_whatsapp_app.scanner import FileRecord, check_storage_access, scan_files
from clean_whatsapp_app.i18n import I18n
from clean_whatsapp_app.ui import UI


def base_cfg(media_base: str) -> dict:
    cfg = dict(DEFAULTS)
    cfg.update(
        {
            "language": "en",
            "media_base": media_base,
            "age_keep_days": 60,
            "age_trash_min": 61,
            "age_trash_max": 180,
            "include_private": False,
            "include_sent": True,
            "show_top_files": 10,
        }
    )
    return normalize_config(cfg)


class CoreSafetyTests(unittest.TestCase):
    def test_wrong_folder_is_reported(self) -> None:
        ok, reason_key, params = check_storage_access("/path/that/does/not/exist")
        self.assertFalse(ok)
        self.assertEqual(reason_key, "folder_missing")
        self.assertIn("media_base", params)

    def test_permission_error_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("clean_whatsapp_app.scanner.os.listdir", side_effect=PermissionError):
                ok, reason_key, _params = check_storage_access(tmp)
        self.assertFalse(ok)
        self.assertEqual(reason_key, "permission_denied")

    def test_invalid_config_is_detected(self) -> None:
        cfg = normalize_config(
            {
                "media_base": "",
                "age_keep_days": 90,
                "age_trash_min": 30,
                "age_trash_max": 10,
                "show_top_files": 0,
            }
        )
        errors = validate_config(cfg)
        self.assertIn("config_error_media_base", errors)
        self.assertIn("config_error_age_order", errors)
        self.assertIn("config_error_top_files", errors)

    def test_scan_ignores_file_removed_during_scan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "WhatsApp" / "Media"
            img = base / "WhatsApp Images"
            img.mkdir(parents=True)
            file_path = img / "old.jpg"
            file_path.write_bytes(b"x")
            now = time.time()
            os.utime(file_path, (now - 70 * 86400, now - 70 * 86400))

            original_stat = os.stat

            def deleting_stat(path):
                if str(path) == str(file_path):
                    file_path.unlink()
                    raise FileNotFoundError(path)
                return original_stat(path)

            with mock.patch("clean_whatsapp_app.scanner.os.stat", side_effect=deleting_stat):
                records, summary = scan_files(str(base), base_cfg(str(base)))

        self.assertEqual(records, [])
        self.assertEqual(summary["total_files"], 0)

    def test_scan_respects_media_type_filters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "WhatsApp" / "Media"
            img = base / "WhatsApp Images"
            vid = base / "WhatsApp Video"
            aud = base / "WhatsApp Audio"
            stickers = base / "WhatsApp Stickers"
            for folder in (img, vid, aud, stickers):
                folder.mkdir(parents=True)
            now = time.time()
            for path in (img / "photo.jpg", vid / "clip.mp4", aud / "sound.mp3", stickers / "sticker.webp"):
                path.write_bytes(b"x")
                os.utime(path, (now - 70 * 86400, now - 70 * 86400))

            cfg = base_cfg(str(base))
            cfg["include_images"] = False
            cfg["include_audio"] = False
            records, summary = scan_files(str(base), cfg)

        self.assertEqual({r.media_type for r in records}, {"video", "stickers"})
        self.assertEqual(summary["total_files"], 2)

    def test_action_records_error_when_file_was_removed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "WhatsApp" / "Media"
            base.mkdir(parents=True)
            missing = base / "missing.jpg"
            record = FileRecord(str(missing), "missing.jpg", 10, time.time() - 70 * 86400, 70, "trash", "images")

            result = perform_actions([record], base_cfg(str(base)), apply_moves=True, apply_deletes=False, logs_dir=Path(tmp) / "logs")

        self.assertEqual(result["moved_count"], 0)
        self.assertEqual(len(result["errors"]), 1)
        self.assertTrue(result["log_path"])

    def test_restore_preview_skips_missing_trash_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "log.json"
            log_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "src": str(Path(tmp) / "original.jpg"),
                                "dst": str(Path(tmp) / "trash" / "missing.jpg"),
                                "planned_dst": str(Path(tmp) / "trash" / "missing.jpg"),
                                "action": "move",
                                "size": 10,
                                "mtime": time.time(),
                                "error": None,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            restorable, skipped = preview_restore_from_log(str(log_path))

        self.assertEqual(restorable, [])
        self.assertEqual(skipped[0]["reason_key"], "restore_reason_missing")

    def test_locale_files_have_same_keys(self) -> None:
        key_sets = locale_key_sets()
        english = key_sets["en"]
        for language in LANGUAGES:
            self.assertEqual(english, key_sets[language], language)

    def test_update_check_only_reports_different_commits(self) -> None:
        ui = UI(base_cfg("/tmp"), I18n("en"))

        def same_commit_run(args, **_kwargs):
            result = mock.Mock()
            result.returncode = 0
            result.stdout = "abc\n" if args[:2] == ["git", "rev-parse"] else ""
            result.stderr = ""
            return result

        with mock.patch("clean_whatsapp_app.ui.subprocess.run", side_effect=same_commit_run):
            self.assertFalse(ui.check_for_updates_silent())

        def different_commit_run(args, **_kwargs):
            result = mock.Mock()
            result.returncode = 0
            if args == ["git", "rev-parse", "HEAD"]:
                result.stdout = "abc\n"
            elif args == ["git", "rev-parse", "origin/main"]:
                result.stdout = "def\n"
            else:
                result.stdout = ""
            result.stderr = ""
            return result

        with mock.patch("clean_whatsapp_app.ui.subprocess.run", side_effect=different_commit_run):
            self.assertTrue(ui.check_for_updates_silent())


if __name__ == "__main__":
    unittest.main()
