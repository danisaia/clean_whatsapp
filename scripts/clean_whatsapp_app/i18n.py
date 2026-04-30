from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCALES_DIR = PROJECT_ROOT / "locales"

LANGUAGES = {
    "en": "English",
    "pt": "Português do Brasil",
    "es": "Español",
    "fr": "Français",
}


class I18n:
    def __init__(self, language: str | None = None) -> None:
        self._cache: Dict[str, Dict[str, str]] = {}
        self.language = "en"
        self.set_language(language or "en")

    def set_language(self, language: str) -> None:
        self.language = language if language in LANGUAGES else "en"
        self._load(self.language)
        self._load("en")

    def t(self, key: str, **kwargs) -> str:
        value = self._cache.get(self.language, {}).get(key)
        if value is None:
            value = self._cache.get("en", {}).get(key, key)
        return value.format(**kwargs) if kwargs else value

    def _load(self, language: str) -> None:
        if language in self._cache:
            return
        path = LOCALES_DIR / f"{language}.json"
        with path.open("r", encoding="utf-8") as f:
            self._cache[language] = json.load(f)


def locale_key_sets() -> Dict[str, set[str]]:
    keys = {}
    for language in LANGUAGES:
        path = LOCALES_DIR / f"{language}.json"
        with path.open("r", encoding="utf-8") as f:
            keys[language] = set(json.load(f).keys())
    return keys

