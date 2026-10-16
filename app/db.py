"""Local SQLite store for manually-entered tie-up/genre history.

Purpose: power autocomplete (so re-typing the same anime title across an
album/discography is quick) and grow the genre vocabulary. The editor's
fields themselves are filled from each file's own tags, not from here.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from app.models import DEFAULT_GENRE_VOCABULARY, ManualTagInput


def _data_dir() -> Path:
    # A distributed .exe may sit somewhere read-only (e.g. Program Files), so keep the
    # DB in the user's %LOCALAPPDATA%\dj-tags; from source, use the project's data/.
    if getattr(sys, "frozen", False):
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "dj-tags"
    return Path(__file__).resolve().parent.parent / "data"


DB_PATH = _data_dir() / "dj_tags.sqlite3"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS manual_tag_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artist TEXT NOT NULL,
    album TEXT NOT NULL,
    tie_up_name TEXT NOT NULL DEFAULT '',
    op_ed_type TEXT NOT NULL DEFAULT '',
    genres TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_manual_tag_history_artist ON manual_tag_history(artist);
CREATE INDEX IF NOT EXISTS idx_manual_tag_history_album ON manual_tag_history(artist, album);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(_SCHEMA)
    return conn


def save_entry(artist: str, album: str, manual: ManualTagInput) -> None:
    if not (manual.tie_up_name or manual.op_ed_type or manual.genres):
        return
    with closing(_connect()) as conn:
        conn.execute(
            "INSERT INTO manual_tag_history (artist, album, tie_up_name, op_ed_type, genres, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                artist,
                album,
                manual.tie_up_name,
                manual.op_ed_type,
                ",".join(manual.genres),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()


def get_tie_up_suggestions(artist: str = "") -> list[str]:
    """Distinct tie-up names, most-recently-used first; scoped to artist when given."""
    with closing(_connect()) as conn:
        if artist:
            rows = conn.execute(
                "SELECT DISTINCT tie_up_name FROM manual_tag_history"
                " WHERE artist = ? AND tie_up_name != '' ORDER BY id DESC",
                (artist,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT DISTINCT tie_up_name FROM manual_tag_history"
                " WHERE tie_up_name != '' ORDER BY id DESC",
            ).fetchall()
    return [r[0] for r in rows]


def get_genre_vocabulary() -> list[str]:
    """Default anime-genre tag list plus anything the user has typed before."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT genres FROM manual_tag_history WHERE genres != ''"
        ).fetchall()
    used = {g for (genres,) in rows for g in genres.split(",") if g}
    return sorted(used | set(DEFAULT_GENRE_VOCABULARY))
