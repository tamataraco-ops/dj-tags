from __future__ import annotations

from pathlib import Path

AUDIO_EXTENSIONS = {".mp3", ".m4a"}


def find_audio_files(folder: str) -> list[str]:
    """Recursively collect MP3/M4A file paths under folder, sorted for stable ordering."""
    root = Path(folder)
    if not root.exists():
        return []
    paths = [
        str(p) for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
    ]
    return sorted(paths)
