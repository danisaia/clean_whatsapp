from __future__ import annotations

from .config import ensure_dirs, load_config
from .i18n import I18n
from .ui import UI


def main() -> None:
    cfg = load_config()
    ensure_dirs()
    i18n = I18n(cfg.get("language") or "en")
    ui = UI(cfg, i18n)
    ui.main_menu()

