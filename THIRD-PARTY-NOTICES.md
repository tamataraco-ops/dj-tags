# Third-Party Notices / 同梱ソフトウェアのライセンス

DJ Tags の配布物（`dj-tags.exe` とその `_internal` フォルダ）には、以下のソフトウェアが含まれています。
各ライセンスの全文は `licenses/` フォルダにあります。DJ Tags 本体のライセンスは `LICENSE`（GNU GPL v3）です。

| ソフトウェア | バージョン | ライセンス | 全文 | 入手元 / ソースコード |
|---|---|---|---|---|
| Python | 3.14.5 | PSF License | `licenses/Python-PSF.txt` | https://www.python.org/downloads/source/ |
| Qt | 6.11.2 | LGPL-3.0 | `licenses/Qt-PySide6-LGPL-3.0.txt` | https://download.qt.io/official_releases/qt/6.11/6.11.2/ |
| PySide6 / Shiboken6 (Qt for Python) | 6.11.2 | LGPL-3.0 | `licenses/Qt-PySide6-LGPL-3.0.txt` | https://download.qt.io/official_releases/QtForPython/ |
| FFmpeg（Qt Multimedia に同梱） | 7.1.5 | LGPL-2.1-or-later | `licenses/FFmpeg-LGPL-2.1.txt` | https://ffmpeg.org/releases/ffmpeg-7.1.5.tar.xz |
| mutagen | 1.48.1 | GPL-2.0-or-later | `licenses/mutagen-GPL-2.0.txt` | https://github.com/quodlibet/mutagen |
| requests | 2.34.2 | Apache-2.0 | `licenses/requests-Apache-2.0.txt`, `licenses/requests-NOTICE.txt` | https://github.com/psf/requests |
| urllib3 | 2.7.0 | MIT | `licenses/urllib3-MIT.txt` | https://github.com/urllib3/urllib3 |
| idna | 3.19 | BSD-3-Clause | `licenses/idna-BSD-3-Clause.txt` | https://github.com/kjd/idna |
| charset-normalizer | 3.5.1 | MIT | `licenses/charset_normalizer-MIT.txt` | https://github.com/jawah/charset_normalizer |
| certifi | 2026.07.22 | MPL-2.0 | `licenses/certifi-MPL-2.0.txt` | https://github.com/certifi/python-certifi |
| PyInstaller（ブートローダー） | 6.22.3 | GPL-2.0-or-later（ブートローダー例外付き） | `licenses/PyInstaller-GPL-2.0-with-bootloader-exception.txt` | https://github.com/pyinstaller/pyinstaller |

## GPL について

mutagen が GPL-2.0-or-later のため、DJ Tags 全体を GNU GPL v3 で配布しています（GPL v3 は LGPL-3.0 の Qt と両立します）。
DJ Tags のソースコードは README に記載のリポジトリで公開しています。

## Qt / PySide6 / FFmpeg（LGPL）について

- これらのライブラリは改変せずに使用しており、`_internal\PySide6\` などに独立した DLL として同梱しています。
  利用者は、互換性のある別バージョン・改変版の DLL に差し替えて DJ Tags を動かすことができます。
- 対応するソースコードは上の表の入手元から取得できます。入手できなくなった場合は、
  README 記載のリポジトリの Issue でご連絡ください。ソースコードを提供します。
- FFmpeg は Qt が LGPL 構成でビルドしたもの（GPL 専用コンポーネントを含まない）をそのまま同梱しています。

## PyInstaller について

PyInstaller はブートローダー例外付きの GPL で、PyInstaller で作った実行ファイルは任意のライセンスで配布できます。
ライセンス全文は参考として同梱しています。
