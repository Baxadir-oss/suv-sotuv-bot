"""8-bo'lim: haftalik backup — SQLite faylini oddiy nusxalash, ortiqcha jarayonsiz."""
from __future__ import annotations

import datetime as dt
import shutil
from pathlib import Path

from bot.config import config

BACKUPS_DIR = Path("backups")
KEEP_LAST_N = 4  # oxirgi 4 ta haftalik nusxa yetarli — disk joyi tejaladi


def run_weekly_backup() -> Path:
    BACKUPS_DIR.mkdir(exist_ok=True)
    src = Path(config.db_path)
    if not src.exists():
        raise FileNotFoundError(f"Ma'lumotlar bazasi topilmadi: {src}")

    stamp = dt.datetime.utcnow().strftime("%Y%m%d")
    dest = BACKUPS_DIR / f"suv_bot_{stamp}.db"
    shutil.copy2(src, dest)

    _cleanup_old_backups()
    return dest


def _cleanup_old_backups() -> None:
    backups = sorted(BACKUPS_DIR.glob("suv_bot_*.db"))
    for old in backups[:-KEEP_LAST_N]:
        old.unlink(missing_ok=True)
