"""Tag read/merge/write helpers built on mutagen.

Design rule: writes are additive. We never delete or blindly overwrite an
existing tag value - new information is appended alongside whatever the file
already carries, and re-applying the same value is a no-op. The one exception
is a Grouping segment for the same tie-up, which is replaced (see below).

Field mapping (chosen for Serato DJ compatibility - both are plain ID3/MP4
fields Serato already shows as browsable/searchable columns):
  - Grouping (TIT1 / \xa9grp): tie-up program name + OP/ED type, e.g. "SPY x FAMILY OP"
                                Segments are joined by " / "; one segment per tie-up, so
                                re-applying a tie-up with a different type replaces it.
  - Comment  (COMM / \xa9cmt):  anime genre tags, e.g. "#バトル #スパイ"
  - Cover art (APIC / covr):    jacket thumbnail
  - Title/Artist/Album/Genre:   edited in the UI; existing values are only replaced
                                when the user explicitly opts in per field
"""

from __future__ import annotations

import re
from pathlib import Path

from mutagen.id3 import ID3, ID3NoHeaderError, APIC, COMM, TIT1, TCON, Frames
from mutagen.mp4 import MP4, MP4Cover

from app.models import ManualTagInput, OP_ED_CHOICES, TrackTags

GROUPING_SEP = " / "


def _split_grouping_segment(segment: str) -> tuple[str, str]:
    """'SPY x FAMILY OP' -> ('SPY x FAMILY', 'OP'); no known type suffix -> (segment, '')."""
    for op_ed in OP_ED_CHOICES:
        if not op_ed:
            continue
        if segment == op_ed:
            return "", op_ed
        if segment.endswith(" " + op_ed):
            return segment[: -len(op_ed) - 1].strip(), op_ed
    return segment, ""


def parse_manual_tags(track: TrackTags) -> ManualTagInput:
    """Read back what apply_manual_tags wrote: tie-up/type from Grouping, genres from Comment.

    With several Grouping segments, the last one that names a tie-up is shown (falling
    back to a type-only segment). Only "#tag" words in the comment count as genres.
    """
    segments = [s.strip() for s in track.grouping.split(GROUPING_SEP) if s.strip()]
    parsed = [_split_grouping_segment(s) for s in segments]
    named = [p for p in parsed if p[0]]
    tie_up, op_ed = (named or parsed or [("", "")])[-1]
    genres = re.findall(r"#([^\s#]+)", track.comment)
    return ManualTagInput(tie_up_name=tie_up, op_ed_type=op_ed, genres=genres)


def _merge_grouping(existing: str, tie_up: str, op_ed: str) -> str:
    """Add "tie_up op_ed" to the Grouping text, keeping one segment per tie-up.

    A segment for the same tie-up is replaced in place (so correcting キャラクターソング
    to OP doesn't leave both). Type-only segments (e.g. "OP", written when the tie-up
    name was left blank) are treated as incomplete entries for this track and are
    replaced too when a full "tie_up op_ed" is applied. Segments for other tie-ups and
    anything else already in the field are kept. With no type given, an existing
    segment for the tie-up is left as is.
    """
    tie_up, op_ed = tie_up.strip(), op_ed.strip()
    piece = " ".join(p for p in (tie_up, op_ed) if p)
    if not piece:
        return existing

    def replaces(segment: str) -> bool:
        name, seg_type = _split_grouping_segment(segment)
        if name == tie_up:
            return True
        return bool(tie_up and op_ed and not name and seg_type)

    segments = [s.strip() for s in existing.split(GROUPING_SEP) if s.strip()]
    same = [i for i, s in enumerate(segments) if replaces(s)]
    if not same:
        return GROUPING_SEP.join(segments + [piece])
    if not op_ed:
        return existing
    first = same[0]
    segments[first] = piece
    return GROUPING_SEP.join(s for i, s in enumerate(segments) if i == first or i not in same)


def _merge_hashtags(existing: str, tags: list[str]) -> str:
    """Append each tag as '#tag' unless that exact hashtag substring is already present."""
    result = existing
    for tag in tags:
        tag = tag.strip()
        if not tag:
            continue
        hashtag = tag if tag.startswith("#") else f"#{tag}"
        if hashtag in result:
            continue
        result = f"{result} {hashtag}".strip()
    return result


def is_mp3(path: str) -> bool:
    return path.lower().endswith(".mp3")


def is_m4a(path: str) -> bool:
    return path.lower().endswith(".m4a")


def read_tags(path: str) -> TrackTags:
    if is_mp3(path):
        track = _read_mp3(path)
    elif is_m4a(path):
        track = _read_m4a(path)
    else:
        raise ValueError(f"unsupported file type: {path}")

    # Untagged files: treat the filename (without extension) as the title so the
    # table, editor and artwork search still have something to work with.
    # In-memory only - nothing is written back to the file.
    if not track.title:
        track.title = Path(path).stem
        track.title_from_filename = True
    return track


def _read_mp3(path: str) -> TrackTags:
    try:
        id3 = ID3(path)
    except ID3NoHeaderError:
        id3 = ID3()

    def first_text(frame_id: str) -> str:
        frame = id3.get(frame_id)
        return str(frame.text[0]) if frame and frame.text else ""

    comm_frames = id3.getall("COMM")
    comment = str(comm_frames[0].text[0]) if comm_frames and comm_frames[0].text else ""

    return TrackTags(
        path=path,
        title=first_text("TIT2"),
        artist=first_text("TPE1"),
        album=first_text("TALB"),
        genre=first_text("TCON"),
        grouping=first_text("TIT1"),
        comment=comment,
        has_artwork=bool(id3.getall("APIC")),
    )


def _read_m4a(path: str) -> TrackTags:
    mp4 = MP4(path)
    tags = mp4.tags or {}

    def first(key: str) -> str:
        val = tags.get(key)
        return str(val[0]) if val else ""

    return TrackTags(
        path=path,
        title=first("\xa9nam"),
        artist=first("\xa9ART"),
        album=first("\xa9alb"),
        genre=first("\xa9gen"),
        grouping=first("\xa9grp"),
        comment=first("\xa9cmt"),
        has_artwork=bool(tags.get("covr")),
    )


def apply_manual_tags(path: str, manual: ManualTagInput) -> None:
    """Merge tie-up/OP-ED into Grouping (one segment per tie-up) and genres into Comment."""
    if is_mp3(path):
        _apply_mp3(path, manual)
    elif is_m4a(path):
        _apply_m4a(path, manual)
    else:
        raise ValueError(f"unsupported file type: {path}")


def _apply_mp3(path: str, manual: ManualTagInput) -> None:
    try:
        id3 = ID3(path)
    except ID3NoHeaderError:
        id3 = ID3()

    existing = id3.get("TIT1")
    existing_text = str(existing.text[0]) if existing and existing.text else ""
    merged = _merge_grouping(existing_text, manual.tie_up_name, manual.op_ed_type)
    if merged != existing_text:
        id3.setall("TIT1", [TIT1(encoding=3, text=[merged])])

    if manual.genres:
        comm_frames = id3.getall("COMM")
        existing_text = str(comm_frames[0].text[0]) if comm_frames and comm_frames[0].text else ""
        merged = _merge_hashtags(existing_text, manual.genres)
        # Preserve every other COMM frame (different lang/desc); replace only the one we track.
        others = [f for f in comm_frames[1:]]
        id3.setall("COMM", [COMM(encoding=3, lang="eng", desc="", text=[merged])] + others)

    id3.save(path, v2_version=3)


def _apply_m4a(path: str, manual: ManualTagInput) -> None:
    mp4 = MP4(path)
    if mp4.tags is None:
        mp4.add_tags()
    tags = mp4.tags

    existing = tags.get("\xa9grp")
    existing_text = str(existing[0]) if existing else ""
    merged = _merge_grouping(existing_text, manual.tie_up_name, manual.op_ed_type)
    if merged != existing_text:
        tags["\xa9grp"] = [merged]

    if manual.genres:
        existing = tags.get("\xa9cmt")
        existing_text = str(existing[0]) if existing else ""
        tags["\xa9cmt"] = [_merge_hashtags(existing_text, manual.genres)]

    mp4.save()


FILLABLE_FIELDS = {"title": "タイトル", "artist": "アーティスト", "album": "アルバム", "genre": "ジャンル"}
_MP3_FIELD_FRAMES = {"title": "TIT2", "artist": "TPE1", "album": "TALB", "genre": "TCON"}
_M4A_FIELD_KEYS = {"title": "\xa9nam", "artist": "\xa9ART", "album": "\xa9alb", "genre": "\xa9gen"}


def current_basic_tags(track: TrackTags) -> dict[str, str]:
    """Title/artist/album/genre as stored on disk (a filename-derived title counts as empty)."""
    return {
        "title": "" if track.title_from_filename else track.title,
        "artist": track.artist,
        "album": track.album,
        "genre": track.genre,
    }


def write_basic_tags(path: str, values: dict[str, str]) -> None:
    """Set each given title/artist/album/genre field to its value.

    The caller decides which fields may overwrite existing values; empty values are
    skipped so this never clears a tag.
    """
    values = {k: v.strip() for k, v in values.items() if k in FILLABLE_FIELDS and v and v.strip()}
    if not values:
        return

    if is_mp3(path):
        try:
            id3 = ID3(path)
        except ID3NoHeaderError:
            id3 = ID3()
        for field, value in values.items():
            frame_id = _MP3_FIELD_FRAMES[field]
            id3.setall(frame_id, [Frames[frame_id](encoding=3, text=[value])])
        id3.save(path, v2_version=3)
    elif is_m4a(path):
        mp4 = MP4(path)
        if mp4.tags is None:
            mp4.add_tags()
        for field, value in values.items():
            mp4.tags[_M4A_FIELD_KEYS[field]] = [value]
        mp4.save()
    else:
        raise ValueError(f"unsupported file type: {path}")


def set_artwork(path: str, image_bytes: bytes, mime: str = "image/jpeg") -> None:
    """Embed/replace the front-cover artwork. Leaves every other tag untouched."""
    if is_mp3(path):
        try:
            id3 = ID3(path)
        except ID3NoHeaderError:
            id3 = ID3()
        # Drop only the existing front-cover picture(s); keep any other APIC types.
        kept = [f for f in id3.getall("APIC") if f.type != 3]
        id3.setall("APIC", kept + [APIC(encoding=3, mime=mime, type=3, desc="Cover", data=image_bytes)])
        id3.save(path, v2_version=3)
    elif is_m4a(path):
        mp4 = MP4(path)
        if mp4.tags is None:
            mp4.add_tags()
        fmt = MP4Cover.FORMAT_PNG if mime == "image/png" else MP4Cover.FORMAT_JPEG
        mp4.tags["covr"] = [MP4Cover(image_bytes, imageformat=fmt)]
        mp4.save()
    else:
        raise ValueError(f"unsupported file type: {path}")
