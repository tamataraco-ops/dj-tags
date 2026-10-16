"""Help menu dialogs: the "Appropriate Legal Notices" GPL-3.0 section 5(d) asks
interactive programs to display (copyright, no warranty, where the license is)."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox, QWidget

from app import about


def release_root() -> Path:
    """Folder holding LICENSE / THIRD-PARTY-NOTICES.md / licenses/ (next to the .exe when built)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def show_about(parent: QWidget) -> None:
    QMessageBox.about(
        parent,
        f"{about.APP_NAME} について",
        f"<h3>{about.APP_NAME} {about.VERSION}</h3>"
        f"<p>Copyright (C) {about.COPYRIGHT_YEAR} {about.AUTHOR}</p>"
        "<p>このプログラムはフリーソフトウェアです。GNU General Public License "
        "バージョン 3 (またはそれ以降) の条件に従って再配布・改変できます。</p>"
        "<p>このプログラムは<b>無保証</b>です。商品性や特定目的への適合性の黙示的保証も含め、"
        "いかなる保証もありません。タグの書き込みは音楽ファイルを直接変更するため、"
        "事前にバックアップを取ってください。</p>"
        f'<p>ソースコード: <a href="{about.REPO_URL}">{about.REPO_URL}</a></p>'
        "<p>曲名・アーティスト名で検索すると、その文字列が Apple (iTunes Search API) と "
        "MusicBrainz / Cover Art Archive に送信されます。</p>"
        "<p>iTunes Search API の結果は、試聴（ストリーミングのみ）・ストアページへのリンク・"
        "参考表示にのみ使用し、iTunes のジャケット画像はファイルに埋め込みません。"
        "試聴音源とストア情報は provided courtesy of iTunes です。</p>"
        "<p>iTunes は Apple Inc. の商標です。本ソフトウェアは Apple Inc.、MusicBrainz "
        "(MetaBrainz Foundation)、Serato とは無関係で、これらから承認を受けたものではありません。</p>",
    )


def open_license_info(parent: QWidget) -> None:
    notices = release_root() / "THIRD-PARTY-NOTICES.md"
    if notices.exists():
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(release_root())))
    else:
        QMessageBox.information(
            parent, "ライセンス情報",
            f"ライセンス文書が見つかりません。\n{about.REPO_URL} を参照してください。",
        )
