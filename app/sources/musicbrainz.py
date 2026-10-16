"""MusicBrainz + Cover Art Archive client - free, no API key, but rate-limited to 1 req/sec
and requires an identifying User-Agent (https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting).
"""

from __future__ import annotations

import time

import requests

from app.about import USER_AGENT
from app.models import ArtworkCandidate

SEARCH_URL = "https://musicbrainz.org/ws/2/recording/"
COVER_ART_URL = "https://coverartarchive.org/release/{mbid}/front-500"
HEADERS = {"User-Agent": USER_AGENT}
TIMEOUT = 10

_last_request_at = 0.0


def _throttle() -> None:
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    _last_request_at = time.monotonic()


def search(artist: str, title: str, limit: int = 5) -> list[ArtworkCandidate]:
    """Search MusicBrainz recordings, then check Cover Art Archive for each candidate's release."""
    if not artist and not title:
        return []

    query = f'artist:"{artist}" AND recording:"{title}"' if artist else f'recording:"{title}"'
    _throttle()
    try:
        resp = requests.get(
            SEARCH_URL,
            params={"query": query, "fmt": "json", "limit": limit},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        recordings = resp.json().get("recordings", [])
    except (requests.RequestException, ValueError):
        return []

    candidates: list[ArtworkCandidate] = []
    for rec in recordings:
        releases = rec.get("releases", [])
        if not releases:
            continue
        mbid = releases[0].get("id")
        if not mbid:
            continue
        candidates.append(
            ArtworkCandidate(
                source="MusicBrainz",
                artwork_url=COVER_ART_URL.format(mbid=mbid),
                title=rec.get("title", ""),
                artist=", ".join(a.get("name", "") for a in rec.get("artist-credit", []) if isinstance(a, dict)),
                album=releases[0].get("title", ""),
            )
        )
    return candidates


def download_image(url: str) -> bytes:
    _throttle()
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.content
