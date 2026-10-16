from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ArtworkCandidate:
    """One jacket image option returned by an external source."""

    source: str  # "iTunes" or "MusicBrainz"
    artwork_url: str
    title: str = ""
    artist: str = ""
    album: str = ""
    genre: str = ""
    preview_url: str = ""  # ~30s audio sample (iTunes only; MusicBrainz has none)


@dataclass
class TrackTags:
    """Snapshot of a file's relevant tag fields, read via mutagen."""

    path: str
    title: str = ""
    artist: str = ""
    album: str = ""
    genre: str = ""
    grouping: str = ""
    comment: str = ""
    has_artwork: bool = False
    title_from_filename: bool = False  # title tag was empty; title holds the filename stem


@dataclass
class ManualTagInput:
    """User-entered enrichment for a track, applied on top of existing tags."""

    tie_up_name: str = ""
    op_ed_type: str = ""  # "OP" / "ED" / "挿入歌" / "劇伴" / "イメージソング" / "キャラクターソング"
    genres: list[str] = field(default_factory=list)


OP_ED_CHOICES = [
    "",
    "OP",
    "ED",
    "挿入歌",
    "劇伴",
    "イメージソング",
    "キャラクターソング",
]

DEFAULT_GENRE_VOCABULARY = [
    "ロボット", "バトル", "異世界", "学園", "恋愛", "スポーツ", "日常",
    "SF", "ファンタジー", "ホラー", "ミステリー", "音楽/アイドル",
    "ギャグ/コメディ", "戦争", "歴史", "スチームパンク", "サイバーパンク",
    "魔法少女", "特撮", "青春", "サスペンス",
]
