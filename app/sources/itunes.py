"""iTunes Search API client - free, no API key required.

Docs: https://performance-partners.apple.com/search-api
"""

from __future__ import annotations

import requests

from app.models import ArtworkCandidate

SEARCH_URL = "https://itunes.apple.com/search"
TIMEOUT = 10


def _upsize_artwork(url: str, size: int = 1200) -> str:
    """iTunes artwork URLs embed their resolution in the path, e.g. .../100x100bb.jpg."""
    for token in ("100x100bb", "600x600bb", "60x60bb"):
        if token in url:
            return url.replace(token, f"{size}x{size}bb")
    return url


def search(artist: str, title: str, country: str = "JP", limit: int = 5) -> list[ArtworkCandidate]:
    """Search iTunes for a song by artist/title. Tries the given storefront, falls back to US."""
    term = f"{artist} {title}".strip()
    if not term:
        return []

    for storefront in (country, "US"):
        try:
            resp = requests.get(
                SEARCH_URL,
                params={
                    "term": term,
                    "media": "music",
                    "entity": "song",
                    "limit": limit,
                    "country": storefront,
                },
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
        except (requests.RequestException, ValueError):
            results = []

        if results:
            return [
                ArtworkCandidate(
                    source="iTunes",
                    artwork_url=_upsize_artwork(r.get("artworkUrl100", "")),
                    title=r.get("trackName", ""),
                    artist=r.get("artistName", ""),
                    album=r.get("collectionName", ""),
                    genre=r.get("primaryGenreName", ""),
                    preview_url=r.get("previewUrl", ""),
                )
                for r in results
                if r.get("artworkUrl100")
            ]

    return []


def download_image(url: str) -> bytes:
    resp = requests.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.content
