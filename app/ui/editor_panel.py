from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QSettings, QSize, QStringListModel, QUrl
from PySide6.QtGui import QDesktopServices, QPainter, QPixmap
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QComboBox,
    QListWidget, QListWidgetItem, QPushButton, QAbstractItemView, QGroupBox,
    QMessageBox, QCompleter, QScrollArea, QDialog, QDialogButtonBox, QCheckBox, QSlider,
)

from app import db, tags
from app.models import ArtworkCandidate, ManualTagInput, OP_ED_CHOICES, TrackTags
from app.ui.workers import ArtworkSearchWorker, ImageDownloadWorker

# Set the text color explicitly: the light background alone leaves white text
# unreadable under a dark system theme.
CHANGED_FIELD_STYLE = "background-color: #fff3c4; color: #000000;"
# Mid gray that stays readable on both light and dark system themes.
MUTED_TEXT = "#9a9a9a"
DEFAULT_VOLUME = 70


class OverwriteDialog(QDialog):
    """Lists fields that will be newly filled and lets the user opt in, per field,
    to overwriting fields that already have a value."""

    def __init__(self, fills: dict[str, str], conflicts: dict[str, tuple[str, str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("タグの適用")
        layout = QVBoxLayout(self)

        if fills:
            layout.addWidget(QLabel("空欄に書き込む項目:"))
            for field, value in fills.items():
                layout.addWidget(QLabel(f"　{tags.FILLABLE_FIELDS[field]}: {value}"))

        layout.addWidget(QLabel("既に値がある項目 (チェックしたものだけ上書きします):"))
        self.checkboxes: dict[str, QCheckBox] = {}
        for field, (old, new) in conflicts.items():
            cb = QCheckBox(f"{tags.FILLABLE_FIELDS[field]}: {old}  →  {new}")
            layout.addWidget(cb)
            self.checkboxes[field] = cb

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("適用")
        buttons.button(QDialogButtonBox.Cancel).setText("キャンセル")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_fields(self) -> set[str]:
        return {f for f, cb in self.checkboxes.items() if cb.isChecked()}


class EditorPanel(QWidget):
    track_updated = Signal(str)  # path of the track that changed on disk
    apply_to_album_requested = Signal(str, str, object)  # artist, album, ManualTagInput

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_track: TrackTags | None = None
        self.artwork_candidates: list[ArtworkCandidate] = []
        self.pending_artwork_bytes: bytes | None = None
        self.selected_candidate: ArtworkCandidate | None = None
        self._search_worker: ArtworkSearchWorker | None = None
        self._download_worker: ImageDownloadWorker | None = None

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)

        self._build_ui()

        self.player.positionChanged.connect(self._on_player_position)
        self.player.durationChanged.connect(self._on_player_duration)
        self.player.playbackStateChanged.connect(self._on_player_state)
        self.player.errorOccurred.connect(lambda _err, msg: self.now_playing_label.setText(f"再生エラー: {msg}"))
        self._on_player_state(QMediaPlayer.StoppedState)

        self.set_track(None)

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)
        content = QWidget()
        scroll.setWidget(content)
        root = QVBoxLayout(content)

        root.setSpacing(8)

        self.title_label = QLabel("トラックを選択してください")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 15px;")
        root.addWidget(self.title_label)

        self.existing_info_label = QLabel("")
        self.existing_info_label.setWordWrap(True)
        self.existing_info_label.setStyleSheet(f"color: {MUTED_TEXT};")
        root.addWidget(self.existing_info_label)

        # --- playback ---
        play_box = QGroupBox("再生")
        play_layout = QVBoxLayout(play_box)
        play_layout.setSpacing(4)

        transport_row = QHBoxLayout()
        self.play_file_btn = QPushButton("▶ ファイル")
        self.play_file_btn.setToolTip("選択中のファイルを再生します")
        self.play_file_btn.clicked.connect(self._on_play_file)
        transport_row.addWidget(self.play_file_btn)
        self.pause_btn = QPushButton("⏸")
        self.pause_btn.setToolTip("一時停止 / 再開")
        self.pause_btn.setFixedWidth(36)
        self.pause_btn.clicked.connect(self._on_pause_toggle)
        transport_row.addWidget(self.pause_btn)
        self.stop_btn = QPushButton("■")
        self.stop_btn.setToolTip("停止")
        self.stop_btn.setFixedWidth(36)
        self.stop_btn.clicked.connect(self.stop_playback)
        transport_row.addWidget(self.stop_btn)
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.sliderMoved.connect(self.player.setPosition)
        transport_row.addWidget(self.seek_slider, 1)
        self.time_label = QLabel("0:00 / 0:00")
        transport_row.addWidget(self.time_label)
        play_layout.addLayout(transport_row)

        status_row = QHBoxLayout()
        self.now_playing_label = QLabel("")
        self.now_playing_label.setStyleSheet(f"color: {MUTED_TEXT};")
        status_row.addWidget(self.now_playing_label, 1)
        self.mute_btn = QPushButton("🔊")
        self.mute_btn.setToolTip("ミュート")
        self.mute_btn.setFixedWidth(36)
        self.mute_btn.setCheckable(True)
        self.mute_btn.toggled.connect(self._on_mute_toggled)
        status_row.addWidget(self.mute_btn)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setFixedWidth(140)
        self.volume_slider.setToolTip("音量")
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        status_row.addWidget(self.volume_slider)
        self.volume_label = QLabel("")
        self.volume_label.setFixedWidth(36)
        status_row.addWidget(self.volume_label)
        play_layout.addLayout(status_row)
        root.addWidget(play_box)

        self.volume_slider.setValue(_load_volume())
        self._on_volume_changed(self.volume_slider.value())

        # --- search ---
        search_box = QGroupBox("検索 (iTunes / MusicBrainz)")
        search_layout = QHBoxLayout(search_box)
        search_layout.addWidget(QLabel("曲名:"))
        self.search_title_edit = QLineEdit()
        self.search_title_edit.returnPressed.connect(self._on_search_clicked)
        search_layout.addWidget(self.search_title_edit, 2)
        search_layout.addWidget(QLabel("アーティスト:"))
        self.search_artist_edit = QLineEdit()
        self.search_artist_edit.returnPressed.connect(self._on_search_clicked)
        search_layout.addWidget(self.search_artist_edit, 1)
        self.search_btn = QPushButton("検索")
        self.search_btn.clicked.connect(self._on_search_clicked)
        search_layout.addWidget(self.search_btn)
        root.addWidget(search_box)

        # --- candidates (artwork preview + list) ---
        candidate_box = QGroupBox("候補 (クリックでジャケットとタグ情報を表示)")
        candidate_layout = QHBoxLayout(candidate_box)

        self.cover_preview = QLabel("(未選択)")
        self.cover_preview.setFixedSize(200, 200)
        self.cover_preview.setAlignment(Qt.AlignCenter)
        self.cover_preview.setStyleSheet("border: 1px solid #999;")
        self.cover_preview.setScaledContents(True)
        candidate_layout.addWidget(self.cover_preview)

        right_col = QVBoxLayout()
        self.candidate_list = QListWidget()
        self.candidate_list.itemClicked.connect(self._on_candidate_clicked)
        right_col.addWidget(self.candidate_list)

        # iTunes terms: previews must sit next to a link to the store page and carry
        # the "provided courtesy of iTunes" credit, so they live here, not in the player box.
        self.itunes_row = QWidget()
        itunes_layout = QHBoxLayout(self.itunes_row)
        itunes_layout.setContentsMargins(0, 0, 0, 0)
        self.play_preview_btn = QPushButton("▶ 試聴")
        self.play_preview_btn.setToolTip("この曲の約30秒の試聴音源をストリーミング再生します")
        self.play_preview_btn.clicked.connect(self._on_play_preview)
        itunes_layout.addWidget(self.play_preview_btn)
        self.store_link_btn = _apple_music_badge_button()
        self.store_link_btn.clicked.connect(self._on_open_store)
        itunes_layout.addWidget(self.store_link_btn)
        courtesy = QLabel("Provided courtesy of iTunes")
        courtesy.setStyleSheet(f"color: {MUTED_TEXT};")
        itunes_layout.addWidget(courtesy, 1)
        right_col.addWidget(self.itunes_row)

        self.artwork_note_label = QLabel(
            "※ iTunes の候補は試聴・参考情報のみです。ジャケットをファイルに埋め込むには "
            "MusicBrainz の候補を選んでください。"
        )
        self.artwork_note_label.setWordWrap(True)
        self.artwork_note_label.setStyleSheet(f"color: {MUTED_TEXT};")
        right_col.addWidget(self.artwork_note_label)

        candidate_layout.addLayout(right_col)
        root.addWidget(candidate_box)

        # --- basic tag editor ---
        tag_box = QGroupBox("タグ編集 (候補クリックで自動入力・手入力も可)")
        tag_layout = QVBoxLayout(tag_box)
        grid = QGridLayout()
        grid.addWidget(QLabel("<b>項目</b>"), 0, 0)
        grid.addWidget(QLabel("<b>適用する値</b>"), 0, 1)
        grid.addWidget(QLabel("<b>現在の値</b>"), 0, 2)
        self.tag_edits: dict[str, QLineEdit] = {}
        self.current_value_labels: dict[str, QLabel] = {}
        for row, (field, label) in enumerate(tags.FILLABLE_FIELDS.items(), start=1):
            grid.addWidget(QLabel(label), row, 0)
            edit = QLineEdit()
            edit.textChanged.connect(self._update_changed_highlight)
            grid.addWidget(edit, row, 1)
            current = QLabel("")
            current.setStyleSheet(f"color: {MUTED_TEXT};")
            grid.addWidget(current, row, 2)
            self.tag_edits[field] = edit
            self.current_value_labels[field] = current
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        tag_layout.addLayout(grid)

        tag_btn_row = QHBoxLayout()
        self.apply_tags_btn = QPushButton("タグを適用")
        self.apply_tags_btn.clicked.connect(self._on_apply_tags)
        tag_btn_row.addWidget(self.apply_tags_btn)
        self.apply_artwork_btn = QPushButton("ジャケットのみ適用")
        self.apply_artwork_btn.clicked.connect(self._on_apply_artwork)
        tag_btn_row.addWidget(self.apply_artwork_btn)
        self.apply_both_btn = QPushButton("ジャケット＋タグを適用")
        self.apply_both_btn.clicked.connect(self._on_apply_both)
        tag_btn_row.addWidget(self.apply_both_btn)
        tag_layout.addLayout(tag_btn_row)
        root.addWidget(tag_box)

        # --- manual tag enrichment ---
        manual_box = QGroupBox("タイアップ / アニソン情報 (手動入力)")
        manual_layout = QVBoxLayout(manual_box)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("タイアップ番組名:"))
        self.tie_up_edit = QLineEdit()
        self.tie_up_completer = QCompleter([])
        self.tie_up_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.tie_up_edit.setCompleter(self.tie_up_completer)
        row1.addWidget(self.tie_up_edit)
        row1.addWidget(QLabel("種別:"))
        self.op_ed_combo = QComboBox()
        self.op_ed_combo.addItems(OP_ED_CHOICES)
        row1.addWidget(self.op_ed_combo)
        manual_layout.addLayout(row1)

        manual_layout.addWidget(QLabel("アニメジャンル (複数選択可):"))
        self.genre_list = QListWidget()
        self.genre_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.genre_list.setMaximumHeight(120)
        manual_layout.addWidget(self.genre_list)

        row2 = QHBoxLayout()
        self.new_genre_edit = QLineEdit()
        self.new_genre_edit.setPlaceholderText("新しいジャンルタグを追加...")
        row2.addWidget(self.new_genre_edit)
        add_genre_btn = QPushButton("追加")
        add_genre_btn.clicked.connect(self._on_add_genre)
        row2.addWidget(add_genre_btn)
        manual_layout.addLayout(row2)

        btn_row = QHBoxLayout()
        self.apply_track_btn = QPushButton("このトラックに適用")
        self.apply_track_btn.clicked.connect(self._on_apply_track)
        btn_row.addWidget(self.apply_track_btn)
        self.apply_album_btn = QPushButton("アルバム全体に適用")
        self.apply_album_btn.clicked.connect(self._on_apply_album)
        btn_row.addWidget(self.apply_album_btn)
        manual_layout.addLayout(btn_row)

        root.addWidget(manual_box)
        root.addStretch(1)

        self._refresh_vocabulary()

    def _refresh_vocabulary(self) -> None:
        self.genre_list.clear()
        for genre in db.get_genre_vocabulary():
            self.genre_list.addItem(QListWidgetItem(genre))

    def set_track(self, track: TrackTags | None) -> None:
        self.stop_playback()
        self.current_track = track
        self.artwork_candidates = []
        self.pending_artwork_bytes = None
        self.selected_candidate = None
        self.play_file_btn.setEnabled(track is not None)
        self._update_preview_button()
        self.candidate_list.clear()
        self.cover_preview.setText("(未選択)")
        self.cover_preview.setPixmap(QPixmap())
        self._update_artwork_buttons()

        enabled = track is not None
        for w in (self.search_title_edit, self.search_artist_edit, self.search_btn,
                  *self.tag_edits.values(), self.apply_tags_btn,
                  self.tie_up_edit, self.op_ed_combo, self.genre_list, self.new_genre_edit,
                  self.apply_track_btn, self.apply_album_btn):
            w.setEnabled(enabled)

        if track is None:
            self.title_label.setText("トラックを選択してください")
            self.existing_info_label.setText("")
            self.search_title_edit.clear()
            self.search_artist_edit.clear()
            for field in self.tag_edits:
                self.tag_edits[field].clear()
                self.current_value_labels[field].setText("")
            self._load_manual_fields(ManualTagInput())
            return

        self._show_track_info(track)
        self._reset_tag_edits()
        self.search_title_edit.setText(track.title)
        self.search_artist_edit.setText(track.artist)

        self.tie_up_completer.setModel(QStringListModel(db.get_tie_up_suggestions(track.artist)))
        # Show what this file already carries; a file with no Grouping/Comment data
        # gets all-blank fields (no carry-over from other tracks).
        self._load_manual_fields(tags.parse_manual_tags(track))

        self._start_search(track.artist, track.title)

    def _load_manual_fields(self, manual: ManualTagInput) -> None:
        self.tie_up_edit.setText(manual.tie_up_name)
        idx = self.op_ed_combo.findText(manual.op_ed_type)
        self.op_ed_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._refresh_vocabulary()
        known = {self.genre_list.item(i).text() for i in range(self.genre_list.count())}
        for genre in manual.genres:
            if genre not in known:  # hashtag typed outside this app's vocabulary
                self.genre_list.addItem(QListWidgetItem(genre))
                known.add(genre)
        for i in range(self.genre_list.count()):
            item = self.genre_list.item(i)
            item.setSelected(item.text() in manual.genres)

    def _show_track_info(self, track: TrackTags) -> None:
        self.title_label.setText(f"{track.title or '(タイトル不明)'} / {track.artist or '(アーティスト不明)'}")
        title_note = "※タイトルタグが空のため、ファイル名を曲名として扱っています\n" if track.title_from_filename else ""
        self.existing_info_label.setText(
            title_note
            + f"グルーピング: {track.grouping or '-'}　｜　コメント: {track.comment or '-'}"
            f"　｜　ジャケット: {'あり' if track.has_artwork else 'なし'}"
        )
        for field, value in tags.current_basic_tags(track).items():
            self.current_value_labels[field].setText(value or "(空)")

    def _reset_tag_edits(self) -> None:
        """Load the on-disk title/artist/album/genre into the edit fields."""
        for field, value in tags.current_basic_tags(self.current_track).items():
            self.tag_edits[field].setText(value)
        self._update_changed_highlight()

    def _update_changed_highlight(self) -> None:
        if not self.current_track:
            return
        current = tags.current_basic_tags(self.current_track)
        for field, edit in self.tag_edits.items():
            value = edit.text().strip()
            edit.setStyleSheet(CHANGED_FIELD_STYLE if value and value != current[field] else "")

    def _reload_current_track(self) -> None:
        """Re-read tags from disk after a write, without restarting the search."""
        self.current_track = tags.read_tags(self.current_track.path)
        self._show_track_info(self.current_track)
        self._reset_tag_edits()
        self.track_updated.emit(self.current_track.path)

    # --- search ---

    def _on_search_clicked(self) -> None:
        title = self.search_title_edit.text().strip()
        artist = self.search_artist_edit.text().strip()
        if not title and not artist:
            return
        self._start_search(artist, title)

    def _start_search(self, artist: str, title: str) -> None:
        self.artwork_candidates = []
        self.selected_candidate = None
        self._update_preview_button()
        self.candidate_list.clear()
        self.candidate_list.addItem("検索中...")
        worker = ArtworkSearchWorker(artist, title, self)
        # Ignore results from a search that was superseded by a newer one.
        worker.finished_ok.connect(lambda c: self._on_search_done(c) if worker is self._search_worker else None)
        worker.failed.connect(lambda m: self._on_search_failed(m) if worker is self._search_worker else None)
        self._search_worker = worker
        worker.start()

    def _on_search_done(self, candidates: list[ArtworkCandidate]) -> None:
        self.artwork_candidates = candidates
        self.candidate_list.clear()
        if not candidates:
            self.candidate_list.addItem("候補が見つかりませんでした (曲名・アーティストを変えて再検索してください)")
            return
        for c in candidates:
            label = f"[{c.source}] {c.title} - {c.artist} ({c.album})"
            if not c.can_embed_artwork:
                label += "  ※試聴・参考のみ"
            self.candidate_list.addItem(label)

    def _on_search_failed(self, message: str) -> None:
        self.candidate_list.clear()
        self.candidate_list.addItem(f"検索エラー: {message}")

    def _on_candidate_clicked(self, item: QListWidgetItem) -> None:
        row = self.candidate_list.row(item)
        if row < 0 or row >= len(self.artwork_candidates):
            return
        candidate = self.artwork_candidates[row]
        self.selected_candidate = candidate
        self._update_preview_button()

        # Present the candidate's tag info in the editor; keep the current value
        # for anything the candidate doesn't provide (e.g. MusicBrainz has no genre).
        current = tags.current_basic_tags(self.current_track)
        candidate_values = {"title": candidate.title, "artist": candidate.artist,
                            "album": candidate.album, "genre": candidate.genre}
        for field, edit in self.tag_edits.items():
            edit.setText(candidate_values[field] or current[field])

        self.pending_artwork_bytes = None
        self._update_artwork_buttons()
        self.cover_preview.setPixmap(QPixmap())
        self.cover_preview.setText("読込中...")
        worker = ImageDownloadWorker(candidate, self)
        worker.finished_ok.connect(lambda d: self._on_image_downloaded(d) if worker is self._download_worker else None)
        worker.failed.connect(lambda m: self.cover_preview.setText(f"取得失敗: {m}")
                              if worker is self._download_worker else None)
        self._download_worker = worker
        worker.start()

    def _on_image_downloaded(self, data: bytes) -> None:
        self.pending_artwork_bytes = data
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        self.cover_preview.setPixmap(pixmap)
        self._update_artwork_buttons()

    def _can_embed_selected_artwork(self) -> bool:
        c = self.selected_candidate
        return bool(c and c.can_embed_artwork)

    def _update_artwork_buttons(self) -> None:
        ready = (self.current_track is not None and self.pending_artwork_bytes is not None
                 and self._can_embed_selected_artwork())
        self.apply_artwork_btn.setEnabled(ready)
        self.apply_both_btn.setEnabled(ready)
        blocked = self.selected_candidate is not None and not self._can_embed_selected_artwork()
        tip = "iTunes の候補のジャケットは規約上ファイルに埋め込めません" if blocked else ""
        self.apply_artwork_btn.setToolTip(tip)
        self.apply_both_btn.setToolTip(tip)

    # --- playback ---

    def _update_preview_button(self) -> None:
        """Show the iTunes preview / store link / credit row only for an iTunes candidate."""
        c = self.selected_candidate
        is_itunes = bool(c and c.source == "iTunes")
        self.itunes_row.setVisible(is_itunes)
        self.artwork_note_label.setVisible(is_itunes)
        self.play_preview_btn.setEnabled(bool(c and c.preview_url))
        # Hide rather than disable: a disabled button would draw the badge grayed out,
        # and the guidelines forbid altering the artwork.
        self.store_link_btn.setVisible(bool(c and c.store_url))

    def _on_open_store(self) -> None:
        c = self.selected_candidate
        if c and c.store_url:
            QDesktopServices.openUrl(QUrl(c.store_url))

    def _play(self, source: QUrl, label: str) -> None:
        self.player.stop()
        self.player.setSource(source)
        self.player.play()
        self.now_playing_label.setText(label)

    def _on_play_file(self) -> None:
        if not self.current_track:
            return
        self._play(QUrl.fromLocalFile(self.current_track.path),
                   f"再生中 (ファイル): {self.current_track.title}")

    def _on_play_preview(self) -> None:
        c = self.selected_candidate
        if not c or not c.preview_url:
            return
        self._play(QUrl(c.preview_url), f"試聴中: {c.title} - {c.artist}  (provided courtesy of iTunes)")

    def _on_pause_toggle(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        elif self.player.playbackState() == QMediaPlayer.PausedState:
            self.player.play()

    def stop_playback(self) -> None:
        self.player.stop()
        # Release the file handle so tag writes to the playing file aren't blocked.
        self.player.setSource(QUrl())
        self.now_playing_label.setText("")

    def _on_player_position(self, pos: int) -> None:
        if not self.seek_slider.isSliderDown():
            self.seek_slider.setValue(pos)
        self.time_label.setText(f"{_fmt_ms(pos)} / {_fmt_ms(self.player.duration())}")

    def _on_player_duration(self, duration: int) -> None:
        self.seek_slider.setRange(0, duration)
        self.time_label.setText(f"{_fmt_ms(self.player.position())} / {_fmt_ms(duration)}")

    def _on_player_state(self, state) -> None:
        active = state != QMediaPlayer.StoppedState
        self.pause_btn.setEnabled(active)
        self.stop_btn.setEnabled(active)
        self.pause_btn.setText("▶" if state == QMediaPlayer.PausedState else "⏸")

    def _on_volume_changed(self, value: int) -> None:
        self.audio_output.setVolume(value / 100)
        self.volume_label.setText(f"{value}%")
        _save_volume(value)

    def _on_mute_toggled(self, muted: bool) -> None:
        self.audio_output.setMuted(muted)
        self.mute_btn.setText("🔇" if muted else "🔊")
        self.mute_btn.setToolTip("ミュート解除" if muted else "ミュート")

    # --- applying ---

    def _release_if_playing_file(self) -> None:
        """Windows locks a file while it's open for playback; stop before writing to it."""
        if self.current_track and self.player.source() == QUrl.fromLocalFile(self.current_track.path):
            self.stop_playback()

    def _decide_tag_writes(self) -> dict[str, str] | None:
        """Work out which edited fields to write, asking about overwrites.

        Returns {} when there is nothing to write, None when the user cancelled.
        """
        current = tags.current_basic_tags(self.current_track)
        changes = {f: e.text().strip() for f, e in self.tag_edits.items()
                   if e.text().strip() and e.text().strip() != current[f]}
        fills = {f: v for f, v in changes.items() if not current[f]}
        conflicts = {f: (current[f], v) for f, v in changes.items() if current[f]}
        if not conflicts:
            return fills

        dialog = OverwriteDialog(fills, conflicts, self)
        if dialog.exec() != QDialog.Accepted:
            return None
        return fills | {f: conflicts[f][1] for f in dialog.selected_fields()}

    def _write_tags(self, to_write: dict[str, str]) -> bool:
        self._release_if_playing_file()
        try:
            tags.write_basic_tags(self.current_track.path, to_write)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "エラー", f"タグの書き込みに失敗しました:\n{exc}")
            return False
        return True

    def _write_artwork(self) -> bool:
        self._release_if_playing_file()
        try:
            tags.set_artwork(self.current_track.path, self.pending_artwork_bytes)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "エラー", f"ジャケットの書き込みに失敗しました:\n{exc}")
            return False
        return True

    def _on_apply_tags(self) -> None:
        if not self.current_track:
            return
        to_write = self._decide_tag_writes()
        if to_write is None:
            return
        if not to_write:
            QMessageBox.information(self, "変更なし", "書き込む変更はありません。")
            return
        if self._write_tags(to_write):
            self._reload_current_track()
            QMessageBox.information(self, "完了", "タグを適用しました。")

    def _on_apply_artwork(self) -> None:
        if not self.current_track or not self.pending_artwork_bytes or not self._can_embed_selected_artwork():
            return
        if self._write_artwork():
            self._reload_current_track()
            QMessageBox.information(self, "完了", "ジャケットを適用しました。")

    def _on_apply_both(self) -> None:
        if not self.current_track or not self.pending_artwork_bytes or not self._can_embed_selected_artwork():
            return
        to_write = self._decide_tag_writes()
        if to_write is None:
            return
        if not self._write_artwork():
            return
        if to_write and not self._write_tags(to_write):
            self._reload_current_track()
            return
        self._reload_current_track()
        done = "ジャケットとタグを適用しました。" if to_write else "ジャケットを適用しました (タグの変更はありません)。"
        QMessageBox.information(self, "完了", done)

    def _on_add_genre(self) -> None:
        text = self.new_genre_edit.text().strip()
        if not text:
            return
        for i in range(self.genre_list.count()):
            if self.genre_list.item(i).text() == text:
                self.genre_list.item(i).setSelected(True)
                self.new_genre_edit.clear()
                return
        item = QListWidgetItem(text)
        self.genre_list.addItem(item)
        item.setSelected(True)
        self.new_genre_edit.clear()

    def _collect_manual_input(self) -> ManualTagInput:
        genres = [self.genre_list.item(i).text() for i in range(self.genre_list.count())
                  if self.genre_list.item(i).isSelected()]
        return ManualTagInput(
            tie_up_name=self.tie_up_edit.text().strip(),
            op_ed_type=self.op_ed_combo.currentText(),
            genres=genres,
        )

    def _on_apply_track(self) -> None:
        if not self.current_track:
            return
        manual = self._collect_manual_input()
        self._release_if_playing_file()
        try:
            tags.apply_manual_tags(self.current_track.path, manual)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "エラー", f"タグの書き込みに失敗しました:\n{exc}")
            return
        db.save_entry(self.current_track.artist, self.current_track.album, manual)
        self._reload_current_track()
        QMessageBox.information(self, "完了", "タグを適用しました。")

    def _on_apply_album(self) -> None:
        if not self.current_track:
            return
        manual = self._collect_manual_input()
        db.save_entry(self.current_track.artist, self.current_track.album, manual)
        self.apply_to_album_requested.emit(self.current_track.artist, self.current_track.album, manual)


# Apple Music Identity Guidelines (https://marketing.services.apple/apple-music-identity-guidelines):
# use Apple's artwork unmodified, at least 30px tall on screen, with clear space of at
# least 1/10 of its height, smaller than the content it promotes, and always as a link.
BADGE_HEIGHT = 32
BADGE_CLEAR_SPACE = 4


def _asset_path(name: str) -> Path:
    # PyInstaller unpacks bundled data under sys._MEIPASS (see --add-data in build-release.ps1).
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent.parent))
    return base / "app" / "assets" / name


def _apple_music_badge_button() -> QPushButton:
    """Official "Listen on Apple Music" badge (Japanese) as a link button to the store page."""
    renderer = QSvgRenderer(str(_asset_path("badge.svg")))
    size = renderer.defaultSize()
    width = round(size.width() * BADGE_HEIGHT / size.height())
    btn = QPushButton()
    if renderer.isValid():
        ratio = 2  # render at 2x so the badge stays crisp on high-DPI screens
        pixmap = QPixmap(width * ratio, BADGE_HEIGHT * ratio)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        pixmap.setDevicePixelRatio(ratio)
        btn.setIcon(pixmap)
        btn.setIconSize(QSize(width, BADGE_HEIGHT))
        btn.setFixedSize(width + 2 * BADGE_CLEAR_SPACE, BADGE_HEIGHT + 2 * BADGE_CLEAR_SPACE)
        btn.setFlat(True)
        btn.setStyleSheet("QPushButton { border: none; background: transparent; padding: 0; }")
    else:  # badge file missing: fall back to a plain text link
        btn.setText("Apple Music で聴く")
    btn.setCursor(Qt.PointingHandCursor)
    btn.setToolTip("Apple Music でこの曲のページを開きます")
    return btn


def _load_volume() -> int:
    """Last-used playback volume (0-100), remembered across launches."""
    value = QSettings("dj-tags", "dj-tags").value("playback/volume", DEFAULT_VOLUME)
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return DEFAULT_VOLUME


def _save_volume(value: int) -> None:
    QSettings("dj-tags", "dj-tags").setValue("playback/volume", value)


def _fmt_ms(ms: int) -> str:
    seconds = max(ms, 0) // 1000
    return f"{seconds // 60}:{seconds % 60:02d}"
