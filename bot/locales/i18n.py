"""Oddiy i18n yordamchisi — JSON fayllardan matn oladi va {placeholder}larni to'ldiradi."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

LOCALES_DIR = Path(__file__).parent


@lru_cache(maxsize=8)
def _load(lang: str) -> dict:
    path = LOCALES_DIR / f"{lang}.json"
    if not path.exists():
        path = LOCALES_DIR / "uz.json"
    return json.loads(path.read_text(encoding="utf-8"))


def t(lang: str, key: str, **kwargs) -> str:
    """Berilgan tildagi matnni qaytaradi. Topilmasa — o'zbekcha, u ham bo'lmasa — key."""
    data = _load(lang or "uz")
    value = data.get(key)
    if value is None:
        value = _load("uz").get(key, key)
    if isinstance(value, str) and kwargs:
        try:
            return value.format(**kwargs)
        except KeyError:
            return value
    return value


def t_list(lang: str, key: str) -> list:
    data = _load(lang or "uz")
    value = data.get(key, [])
    if not value:
        value = _load("uz").get(key, [])
    return value
