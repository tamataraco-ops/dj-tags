from __future__ import annotations

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QFileDialog, QLabel, QSplitter,
    QAbstractItemView, QMessageBox, QHeaderView,
)
from PySide6.QtCore import Qt

from app import tags
from app.models import ManualTagInput, TrackTags
from app.scanner import find_audio_files
from app.ui import about_dialog
from app.ui.editor_panel import EditorPanel

COLUMNS = ["タイトル", "アーティスト", "アルバム", "ジャンル", "グルーピング", "コメント", "ジャケット"]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DJ Tags - 音楽タグ管理")
        self.resize(1200, 700)

        self.tracks: dict[str, TrackTags] = {}
        self.row_of_path: dict[str, int] = {}

        self._build_ui()
        self._build_menu()

    def _build_menu(self) -> None:
        help_menu = self.menuBar().addMenu("ヘルプ")
        help_menu.addAction("このアプリについて", lambda: about_dialog.show_about(self))
        help_menu.addAction("ライセンス情報 (フォルダを開く)", lambda: about_dialog.open_license_info(self))

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        top_bar = QHBoxLayout()
        open_btn = QPushButton("フォルダを開く")
        open_btn.clicked.connect(self.open_folder)
        top_bar.addWidget(open_btn)
        self.status_label = QLabel("フォルダが未選択です")
        top_bar.addWidget(self.status_label)
        top_bar.addStretch(1)
        root.addLayout(top_bar)

        splitter = QSplitter(Qt.Horizontal)
        # Stretch 1 so the splitter takes all spare height instead of sharing it with the top bar.
        root.addWidget(splitter, 1)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # Draw the selected row as one flat band (the Windows 11 style otherwise renders each
        # cell as a separate rounded pill with a focus marker).
        self.table.setStyleSheet(
            "QTableWidget { outline: 0; }"
            "QTableWidget::item { padding-left: 4px; border: none; }"
            "QTableWidget::item:selected { background-color: palette(highlight);"
            " color: palette(highlighted-text); border-radius: 0px; }"
        )
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(26)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        splitter.addWidget(self.table)

        self.editor_panel = EditorPanel()
        self.editor_panel.track_updated.connect(self._on_track_updated)
        self.editor_panel.apply_to_album_requested.connect(self._on_apply_to_album)
        splitter.addWidget(self.editor_panel)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([600, 600])

    def open_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "音楽フォルダを選択")
        if not folder:
            return
        paths = find_audio_files(folder)
        if not paths:
            QMessageBox.information(self, "結果なし", "MP3/M4Aファイルが見つかりませんでした。")
            return

        self.tracks.clear()
        self.row_of_path.clear()
        self.table.setRowCount(0)

        for path in paths:
            try:
                track = tags.read_tags(path)
            except Exception:  # noqa: BLE001 - skip unreadable files, keep scanning
                continue
            self._add_row(track)

        self.status_label.setText(f"{self.table.rowCount()} 件のファイルを読み込みました: {folder}")

    def _add_row(self, track: TrackTags) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.tracks[track.path] = track
        self.row_of_path[track.path] = row
        self._fill_row(row, track)

    def _fill_row(self, row: int, track: TrackTags) -> None:
        values = [
            track.title, track.artist, track.album, track.genre,
            track.grouping, track.comment, "あり" if track.has_artwork else "なし",
        ]
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setData(Qt.UserRole, track.path)
            self.table.setItem(row, col, item)

    def _on_selection_changed(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self.editor_panel.set_track(None)
            return
        row = rows[0].row()
        item = self.table.item(row, 0)
        path = item.data(Qt.UserRole) if item else None
        if not path:
            return
        track = tags.read_tags(path)
        self.tracks[path] = track
        self.editor_panel.set_track(track)

    def _on_track_updated(self, path: str) -> None:
        if path not in self.row_of_path:
            return
        track = tags.read_tags(path)
        self.tracks[path] = track
        self._fill_row(self.row_of_path[path], track)

    def _on_apply_to_album(self, artist: str, album: str, manual: ManualTagInput) -> None:
        matches = [p for p, t in self.tracks.items() if t.artist == artist and t.album == album]
        if not matches:
            return
        self.editor_panel.stop_playback()  # a playing file is locked on Windows
        failures: list[str] = []
        for path in matches:
            try:
                tags.apply_manual_tags(path, manual)
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{path}: {exc}")
                continue
            track = tags.read_tags(path)
            self.tracks[path] = track
            self._fill_row(self.row_of_path[path], track)

        if failures:
            QMessageBox.warning(self, "一部失敗", "以下のファイルで失敗しました:\n" + "\n".join(failures))
        else:
            QMessageBox.information(self, "完了", f"アルバム内の {len(matches)} 件に適用しました。")
