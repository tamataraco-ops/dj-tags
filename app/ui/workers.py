"""Background QThreads so network calls (iTunes/MusicBrainz) never block the UI."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from app.models import ArtworkCandidate
from app.sources import itunes, musicbrainz


class ArtworkSearchWorker(QThread):
    finished_ok = Signal(list)  # list[ArtworkCandidate]
    failed = Signal(str)

    def __init__(self, artist: str, title: str, parent=None):
        super().__init__(parent)
        self.artist = artist
        self.title = title

    def run(self) -> None:
        try:
            candidates: list[ArtworkCandidate] = []
            candidates.extend(itunes.search(self.artist, self.title))
            candidates.extend(musicbrainz.search(self.artist, self.title))
            self.finished_ok.emit(candidates)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
            self.failed.emit(str(exc))


class ImageDownloadWorker(QThread):
    finished_ok = Signal(bytes)
    failed = Signal(str)

    def __init__(self, candidate: ArtworkCandidate, parent=None):
        super().__init__(parent)
        self.candidate = candidate

    def run(self) -> None:
        try:
            if self.candidate.source == "MusicBrainz":
                data = musicbrainz.download_image(self.candidate.artwork_url)
            else:
                data = itunes.download_image(self.candidate.artwork_url)
            self.finished_ok.emit(data)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
