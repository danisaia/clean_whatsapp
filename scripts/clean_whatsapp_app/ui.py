from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Dict, Iterable, List

from .actions import perform_actions
from .config import KNOWN_MEDIA_BASES, normalize_config, save_config, validate_config
from .i18n import I18n, LANGUAGES, PROJECT_ROOT
from .restore import list_available_logs, preview_restore_from_log, restore_entries
from .scanner import ACTION_KEYS, check_storage_access, detect_media_base, scan_files
from .version import APP_NAME, APP_VERSION


PRESET_DATA = {
    "1": ("preset_safe_name", "preset_safe_desc", 60, 61, 180),
    "2": ("preset_balanced_name", "preset_balanced_desc", 30, 31, 90),
    "3": ("preset_space_name", "preset_space_desc", 14, 15, 45),
}

MEDIA_LABEL_KEYS = {
    "images": "media_images",
    "animated_gifs": "media_gifs",
    "video": "media_video",
    "audio": "media_audio",
    "voice": "media_voice",
    "stickers": "media_stickers",
    "profile": "media_profile",
    "other": "media_other",
}

ACTION_LABEL_KEYS = {
    "keep": "action_keep",
    "trash": "action_trash",
    "delete": "action_delete",
}


class UI:
    def __init__(self, cfg: Dict, i18n: I18n) -> None:
        self.cfg = normalize_config(cfg)
        self.i18n = i18n

    def t(self, key: str, **kwargs) -> str:
        return self.i18n.t(key, **kwargs)

    def clear_screen(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")

    def header(self, title: str) -> None:
        print("\n" + "=" * 64)
        print(title)
        print("=" * 64)

    def screen(self, title: str) -> None:
        self.clear_screen()
        self.header(title)

    def pause(self) -> None:
        input("\n" + self.t("press_enter"))

    def check_for_updates_silent(self) -> bool:
        try:
            subprocess.run(
                ["git", "fetch", "--quiet", "origin", "main"],
                cwd=PROJECT_ROOT,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            local = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=PROJECT_ROOT,
                check=False,
                text=True,
                capture_output=True,
            )
            remote = subprocess.run(
                ["git", "rev-parse", "origin/main"],
                cwd=PROJECT_ROOT,
                check=False,
                text=True,
                capture_output=True,
            )
        except FileNotFoundError:
            return False
        if local.returncode != 0 or remote.returncode != 0:
            return False
        return local.stdout.strip() != remote.stdout.strip()

    def prompt_yes_no(self, msg: str, default_yes: bool = True) -> bool:
        suffix = self.t("yes_no_default_yes") if default_yes else self.t("yes_no_default_no")
        yes_values = {"y", "yes", "s", "sim", "si", "sí", "o", "oui"}
        no_values = {"n", "no", "nao", "não", "non"}
        while True:
            ans = input(f"{msg} [{suffix}]: ").strip().lower()
            if ans == "":
                return default_yes
            if ans in yes_values:
                return True
            if ans in no_values:
                return False
            print(self.t("yes_no_hint"))

    def prompt_choice(self, msg: str, choices: Iterable[str], default: str) -> str:
        valid = set(choices)
        while True:
            ans = input(f"{msg} [{default}]: ").strip() or default
            if ans in valid:
                return ans
            print(self.t("invalid_option"))

    def prompt_int(self, msg: str, default: int, min_value: int = 0) -> int:
        while True:
            raw = input(f"{msg} [{default}]: ").strip()
            if raw == "":
                return default
            try:
                value = int(raw)
            except ValueError:
                print(self.t("integer_required"))
                continue
            if value < min_value:
                print(self.t("min_value", min_value=min_value))
                continue
            return value

    def strong_confirm(self, msg: str, word: str) -> bool:
        print("\n" + msg)
        print(self.t("confirm_exact", word=word))
        return input("> ").strip() == word

    def human_size(self, n: int) -> str:
        value = float(n)
        for unit in ("B", "KB", "MB", "GB"):
            if value < 1024:
                return f"{value:.1f}{unit}"
            value /= 1024.0
        return f"{value:.1f}TB"

    def select_language(self) -> None:
        self.screen(self.t("select_language_title"))
        print(self.t("select_language_intro", app=APP_NAME) + "\n")
        codes = list(LANGUAGES.keys())
        for idx, code in enumerate(codes, start=1):
            print(f"{idx}) {LANGUAGES[code]}")
        current = self.cfg.get("language")
        default = str(codes.index(current) + 1) if current in codes else "1"
        choice = self.prompt_choice(self.t("choose_language"), {str(i) for i in range(1, len(codes) + 1)}, default)
        self.cfg["language"] = codes[int(choice) - 1]
        self.i18n.set_language(self.cfg["language"])
        save_config(self.cfg)

    def explain_storage_fix(self, media_base: str, reason_key: str, params: Dict) -> None:
        self.header(self.t("storage_missing_title"))
        print(self.t(reason_key, **params))
        print("\n" + self.t("storage_fix_1"))
        print("  termux-setup-storage")
        print("\n" + self.t("storage_fix_2"))
        print("\n" + self.t("configured_folder"))
        print(f"  {media_base}")
        print("\n" + self.t("storage_fix_3"))

    def configure_media_path(self) -> None:
        self.header(self.t("media_path_title"))
        detected = detect_media_base(self.cfg.get("media_base"))
        default_choice = "1"
        if detected in KNOWN_MEDIA_BASES:
            default_choice = str(KNOWN_MEDIA_BASES.index(detected) + 1)
        print(self.t("media_path_intro"))
        print(f"  {detected}")
        print("\n" + self.t("common_folders"))
        for idx, path in enumerate(KNOWN_MEDIA_BASES, start=1):
            marker = self.t("exists") if Path(path).exists() else self.t("not_found")
            print(f"{idx}) {path} ({marker})")
        print(f"4) {self.t('other_path')}")

        choice = self.prompt_choice(self.t("choose_folder"), {"1", "2", "3", "4"}, default_choice)
        if choice in {"1", "2", "3"}:
            self.cfg["media_base"] = KNOWN_MEDIA_BASES[int(choice) - 1]
        else:
            custom = input(self.t("custom_path") + ": ").strip()
            if custom:
                self.cfg["media_base"] = custom
        save_config(self.cfg)

    def apply_preset(self, key: str) -> None:
        _, _, keep, trash_min, trash_max = PRESET_DATA[key]
        self.cfg["age_keep_days"] = keep
        self.cfg["age_trash_min"] = trash_min
        self.cfg["age_trash_max"] = trash_max

    def configure_custom_ages(self) -> None:
        self.header(self.t("custom_ages_title"))
        print(self.t("custom_ages_help"))
        while True:
            keep = self.prompt_int(self.t("keep_until"), int(self.cfg["age_keep_days"]), 0)
            trash_min = self.prompt_int(self.t("trash_from"), int(self.cfg["age_trash_min"]), keep + 1)
            trash_max = self.prompt_int(self.t("trash_until"), int(self.cfg["age_trash_max"]), trash_min)
            if keep < trash_min <= trash_max:
                self.cfg["age_keep_days"] = keep
                self.cfg["age_trash_min"] = trash_min
                self.cfg["age_trash_max"] = trash_max
                save_config(self.cfg)
                return
            print(self.t("age_order_error"))

    def configure_preset_or_custom(self) -> None:
        self.header(self.t("rules_title"))
        print(self.t("rules_intro") + "\n")
        for key, (name_key, desc_key, *_limits) in PRESET_DATA.items():
            extra = f" ({self.t('recommended')})" if key == "1" else ""
            print(f"{key}) {self.t(name_key)}{extra}: {self.t(desc_key)}")
        print(f"4) {self.t('custom')}")

        choice = self.prompt_choice(self.t("choose"), {"1", "2", "3", "4"}, "1")
        if choice == "4":
            self.configure_custom_ages()
        else:
            self.apply_preset(choice)
            save_config(self.cfg)

    def configure_included_folders(self) -> None:
        self.header(self.t("folders_title"))
        print(self.t("sent_help"))
        self.cfg["include_sent"] = self.prompt_yes_no(self.t("include_sent"), bool(self.cfg["include_sent"]))
        print("\n" + self.t("private_help"))
        self.cfg["include_private"] = self.prompt_yes_no(self.t("include_private"), bool(self.cfg["include_private"]))
        self.cfg["show_top_files"] = self.prompt_int(self.t("top_files_count"), int(self.cfg["show_top_files"]), 1)
        save_config(self.cfg)

    def configure_cleanup_filters(self) -> None:
        self.header(self.t("cleanup_filters_title"))
        print(self.t("cleanup_filters_intro"))
        self.cfg["include_images"] = self.prompt_yes_no(self.t("include_images"), bool(self.cfg.get("include_images", True)))
        self.cfg["include_videos"] = self.prompt_yes_no(self.t("include_videos"), bool(self.cfg.get("include_videos", True)))
        self.cfg["include_audio"] = self.prompt_yes_no(self.t("include_audio"), bool(self.cfg.get("include_audio", True)))
        self.cfg["include_stickers"] = self.prompt_yes_no(self.t("include_stickers"), bool(self.cfg.get("include_stickers", True)))
        self.cfg["include_sent"] = self.prompt_yes_no(self.t("include_sent"), bool(self.cfg.get("include_sent", True)))
        self.cfg["include_private"] = self.prompt_yes_no(self.t("include_private"), bool(self.cfg.get("include_private", False)))
        save_config(self.cfg)

    def validate_current_config(self) -> bool:
        errors = validate_config(self.cfg)
        if not errors:
            return True
        self.header(self.t("config_invalid_title"))
        for key in errors:
            print("- " + self.t(key))
        print(self.t("config_invalid_hint"))
        self.pause()
        return False

    def setup_wizard(self) -> None:
        self.screen(self.t("setup_title"))
        print(self.t("setup_intro_1"))
        print(self.t("setup_intro_2"))
        self.cfg["media_base"] = detect_media_base(self.cfg.get("media_base"))
        self.configure_media_path()

        ok, reason_key, params = check_storage_access(self.cfg["media_base"])
        if not ok:
            self.explain_storage_fix(self.cfg["media_base"], reason_key, params)
            self.pause()

        self.configure_preset_or_custom()
        self.configure_included_folders()
        self.cfg["setup_complete"] = True
        save_config(self.cfg)

    def print_config_summary(self) -> None:
        print(self.t("current_config"))
        print(f"  {self.t('folder')}: {self.cfg['media_base']}")
        print(f"  {self.t('keep')}: {self.t('until_days', days=self.cfg['age_keep_days'])}")
        print(f"  {self.t('trash_range', min_days=self.cfg['age_trash_min'], max_days=self.cfg['age_trash_max'])}")
        print(f"  {self.t('delete_above', days=self.cfg['age_trash_max'])}")
        print(f"  {self.t('include_sent_summary')}: {self.t('yes') if self.cfg.get('include_sent') else self.t('no')}")
        print(f"  {self.t('include_private_summary')}: {self.t('yes') if self.cfg.get('include_private') else self.t('no')}")
        print(f"  {self.t('filters_summary')}: {self.enabled_filter_summary()}")
        print(f"  {self.t('language_summary')}: {LANGUAGES.get(self.cfg.get('language'), LANGUAGES['en'])}")

    def enabled_filter_summary(self) -> str:
        items = []
        if self.cfg.get("include_images", True):
            items.append(self.t("filter_images_short"))
        if self.cfg.get("include_videos", True):
            items.append(self.t("filter_videos_short"))
        if self.cfg.get("include_audio", True):
            items.append(self.t("filter_audio_short"))
        if self.cfg.get("include_stickers", True):
            items.append(self.t("filter_stickers_short"))
        return ", ".join(items) if items else self.t("none")

    def print_report(self, records: List, summary: Dict) -> None:
        self.screen(self.t("preview_title"))
        self.print_config_summary()
        print("\n" + self.t("summary"))
        print("  " + self.t("media_analyzed", count=summary["total_files"], size=self.human_size(summary["total_size"])))
        print("  " + self.t("ignored", count=summary["ignored_files"]))
        freeable = summary["by_action"]["trash"]["size"] + summary["by_action"]["delete"]["size"]
        print("  " + self.t("freeable_estimate", size=self.human_size(freeable)))
        if summary["permission_errors"]:
            print("  " + self.t("permission_errors", count=summary["permission_errors"]))

        print("\n" + self.t("what_will_happen"))
        for action in ACTION_KEYS:
            bucket = summary["by_action"][action]
            print(f"  {self.t(ACTION_LABEL_KEYS[action])}: {bucket['count']} ({self.human_size(bucket['size'])})")

        if summary["by_media"]:
            print("\n" + self.t("category_preview_title"))
            for media_type, bucket in sorted(summary["by_media"].items(), key=lambda item: item[1]["size"], reverse=True):
                label = self.t(MEDIA_LABEL_KEYS.get(media_type, "media_other"))
                media_records = [r for r in records if r.media_type == media_type]
                keep_size = sum(r.size for r in media_records if r.action == "keep")
                trash_size = sum(r.size for r in media_records if r.action == "trash")
                delete_size = sum(r.size for r in media_records if r.action == "delete")
                print(f"  {label}: {bucket['count']} ({self.human_size(bucket['size'])})")
                print(f"    {self.t('action_keep')}: {self.human_size(keep_size)} | {self.t('action_trash')}: {self.human_size(trash_size)} | {self.t('action_delete')}: {self.human_size(delete_size)}")

        candidates = [r for r in records if r.action in {"trash", "delete"}]
        if candidates:
            print("\n" + self.t("largest_candidates", count=self.cfg["show_top_files"]))
            for idx, rec in enumerate(sorted(candidates, key=lambda r: r.size, reverse=True)[: int(self.cfg["show_top_files"])], start=1):
                action = self.t(ACTION_LABEL_KEYS[rec.action])
                print(f"  {idx}) {self.human_size(rec.size)} | {rec.age_days} {self.t('days_word')} | {action} | {rec.rel_path}")

    def run_cleanup_flow(self) -> None:
        self.screen(self.t("cleanup_title"))
        if not self.validate_current_config():
            return
        if self.prompt_yes_no(self.t("review_filters_before_scan"), default_yes=True):
            self.configure_cleanup_filters()
        ok, reason_key, params = check_storage_access(self.cfg["media_base"])
        if not ok:
            self.explain_storage_fix(self.cfg["media_base"], reason_key, params)
            self.pause()
            return

        print(self.t("scanning"))
        records, summary = scan_files(self.cfg["media_base"], self.cfg)
        self.print_report(records, summary)

        trash_bucket = summary["by_action"]["trash"]
        delete_bucket = summary["by_action"]["delete"]
        if trash_bucket["count"] == 0 and delete_bucket["count"] == 0:
            print("\n" + self.t("nothing_to_clean"))
            self.pause()
            return

        print("\n" + self.t("preview_only"))
        if not self.prompt_yes_no(self.t("apply_cleanup"), default_yes=False):
            return

        apply_moves = False
        apply_deletes = False
        if trash_bucket["count"]:
            apply_moves = self.prompt_yes_no(self.t("move_to_trash", count=trash_bucket["count"], size=self.human_size(trash_bucket["size"])), default_yes=True)
        if delete_bucket["count"]:
            wants_delete = self.prompt_yes_no(self.t("also_delete", count=delete_bucket["count"], size=self.human_size(delete_bucket["size"])), default_yes=False)
            if wants_delete:
                apply_deletes = self.strong_confirm(self.t("delete_warning"), word=self.t("delete_word"))

        result = perform_actions(records, self.cfg, apply_moves, apply_deletes)
        if not result["log_path"]:
            print("\n" + self.t("no_changes"))
        else:
            for error in result["errors"]:
                print(self.t(error["key"], path=error["path"], error=error["error"]))
            print("\n" + self.t("cleanup_done"))
            print("  " + self.t("moved_count", count=result["moved_count"]))
            print("  " + self.t("deleted_count", count=result["deleted_count"]))
            print("  " + self.t("processed_space", size=self.human_size(result["bytes_processed"])))
            print("  " + self.t("operation_record", path=result["log_path"]))
        self.pause()

    def run_restore_flow(self) -> None:
        self.screen(self.t("restore_title"))
        logs = list_available_logs()
        if not logs:
            print(self.t("no_records"))
            self.pause()
            return

        for idx, path in enumerate(logs[:20], start=1):
            print(f"{idx}) {Path(path).name}")
        print(f"0) {self.t('back')}")

        choice = self.prompt_int(self.t("choose_record"), 1, 0)
        if choice == 0:
            return
        if choice < 1 or choice > min(len(logs), 20):
            print(self.t("invalid_option"))
            self.pause()
            return

        restorable, skipped = preview_restore_from_log(logs[choice - 1])
        self.screen(self.t("restore_preview_title"))
        print(self.t("can_restore", count=len(restorable)))
        print(self.t("cannot_restore", count=len(skipped)))
        for idx, item in enumerate(restorable[:20], start=1):
            entry = item["entry"]
            print(f"  {idx}) {self.human_size(entry.get('size', 0))} | {item['restore_to']}")
        if len(restorable) > 20:
            print("  " + self.t("more_files", count=len(restorable) - 20))
        if skipped:
            print("\n" + self.t("skipped_items"))
            for item in skipped[:10]:
                print(f"  - {item['entry'].get('src')} ({self.t(item['reason_key'])})")
        if not restorable:
            self.pause()
            return
        if not self.prompt_yes_no(self.t("restore_now"), default_yes=False):
            return
        result = restore_entries(restorable)
        for error in result["errors"]:
            print(self.t("restore_failed", path=error["path"], error=error["error"]))
        print("\n" + self.t("restored_count", count=result["restored_count"]))
        self.pause()

    def run_update_flow(self) -> None:
        self.screen(self.t("update_title"))
        print(self.t("update_intro"))
        if not self.prompt_yes_no(self.t("update_confirm"), default_yes=True):
            return
        try:
            completed = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=PROJECT_ROOT,
                check=False,
                text=True,
                capture_output=True,
            )
        except FileNotFoundError:
            print(self.t("update_git_missing"))
            self.pause()
            return

        output = (completed.stdout + "\n" + completed.stderr).strip()
        if output:
            print("\n" + output)
        if completed.returncode == 0:
            print("\n" + self.t("update_done"))
        else:
            print("\n" + self.t("update_failed", code=completed.returncode))
        self.pause()

    def run_settings_flow(self) -> None:
        while True:
            self.screen(self.t("settings_title"))
            self.print_config_summary()
            print(f"\n1) {self.t('menu_profile')}")
            print(f"2) {self.t('menu_ages')}")
            print(f"3) {self.t('menu_folders')}")
            print(f"4) {self.t('menu_path')}")
            print(f"5) {self.t('menu_language')}")
            print(f"6) {self.t('menu_setup')}")
            print(f"7) {self.t('menu_filters')}")
            print(f"0) {self.t('back')}")

            choice = self.prompt_choice(self.t("choose"), {"0", "1", "2", "3", "4", "5", "6", "7"}, "0")
            if choice == "0":
                return
            if choice == "1":
                self.configure_preset_or_custom()
            elif choice == "2":
                self.configure_custom_ages()
            elif choice == "3":
                self.configure_included_folders()
            elif choice == "4":
                self.configure_media_path()
            elif choice == "5":
                self.select_language()
            elif choice == "6":
                self.setup_wizard()
            elif choice == "7":
                self.configure_cleanup_filters()

    def show_help(self) -> None:
        self.screen(self.t("help_title"))
        for key in ("help_1", "help_2", "help_3", "help_4", "help_5"):
            print(self.t(key))
        self.pause()

    def main_menu(self) -> None:
        if self.cfg.get("language") not in LANGUAGES:
            self.select_language()
        if not self.cfg.get("setup_complete"):
            self.setup_wizard()
        update_available = self.check_for_updates_silent()

        while True:
            self.screen(self.t("app_title", version=APP_VERSION))
            if update_available:
                print(self.t("update_available_notice"))
                print()
            self.print_config_summary()
            print(f"\n1) {self.t('menu_analyze')}")
            print(f"2) {self.t('menu_settings')}")
            print(f"3) {self.t('menu_restore')}")
            print(f"4) {self.t('menu_update')}")
            print(f"5) {self.t('menu_help')}")
            print(f"0) {self.t('menu_exit')}")

            choice = self.prompt_choice(self.t("choose"), {"0", "1", "2", "3", "4", "5"}, "1")
            if choice == "1":
                self.run_cleanup_flow()
            elif choice == "2":
                self.run_settings_flow()
            elif choice == "3":
                self.run_restore_flow()
            elif choice == "4":
                self.run_update_flow()
                update_available = self.check_for_updates_silent()
            elif choice == "5":
                self.show_help()
            elif choice == "0":
                print(self.t("exiting"))
                return
