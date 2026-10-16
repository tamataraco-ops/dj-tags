# DJ Tags

アニソンを扱う DJ 向けに、MP3 / M4A ファイルのタグを整理する Windows 用デスクトップアプリです。
タイアップ情報（作品名＋OP/ED など）やアニメのジャンルを、Serato DJ などの DJ ソフトで表示・検索できる項目に書き込みます。

## 主な機能

- フォルダ内の MP3 / M4A を一覧表示（タイトルタグが空の曲はファイル名を曲名として扱います）
- MusicBrainz / Cover Art Archive でジャケット画像と曲情報を検索し、ファイルに書き込み
- iTunes Search API の検索結果で、試聴（約30秒）・ストアページの表示・曲情報の参考表示
  （iTunes のジャケット画像は、規約によりファイルには埋め込みません）
- タイトル・アーティスト・アルバム・ジャンルの編集（既存の値を上書きするかは項目ごとに選べます）
- タイアップ番組名・種別（OP / ED / 挿入歌 など）をグルーピングに、アニメジャンルをコメントに `#タグ` 形式で書き込み
- アルバム単位での一括適用
- 音楽ファイルの再生

### タグの書き込み先

| 内容 | MP3 (ID3v2.3) | M4A |
|---|---|---|
| タイアップ番組名＋種別（例: `SPY x FAMILY OP`） | グルーピング (TIT1) | グルーピング (©grp) |
| アニメジャンル（例: `#バトル #スパイ`） | コメント (COMM) | コメント (©cmt) |
| ジャケット | APIC（表紙） | covr |
| タイトル / アーティスト / アルバム / ジャンル | TIT2 / TPE1 / TALB / TCON | ©nam / ©ART / ©alb / ©gen |

## 動作環境

- Windows 10 / 11（64bit）
- ジャケット・曲情報の検索と試聴にはインターネット接続が必要です

## インストールと起動

1. 配布されている zip を任意の場所に展開します。
2. 展開したフォルダ内の `dj-tags.exe` を起動します。

`dj-tags.exe` は同じフォルダの `_internal` を使って動きます。移動するときは**フォルダごと**移動してください。
コード署名をしていないため、初回起動時に Windows SmartScreen の警告が出ることがあります。

入力履歴（タイアップ名の入力補完など）は `%LOCALAPPDATA%\dj-tags\` に保存されます。アンインストールするときは、展開したフォルダとこのフォルダを削除してください。

## 使い方

1. 「フォルダを開く」で音楽フォルダを選びます。
2. 一覧から曲を選ぶと、右側に曲の情報と検索結果の候補が表示されます。
3. 候補をクリックするとジャケットと曲情報が「タグ編集」欄に入ります。必要に応じて修正し、「タグを適用」「ジャケットのみ適用」「ジャケット＋タグを適用」を押します。
   ジャケットを埋め込めるのは **MusicBrainz の候補**だけです。iTunes の候補（「※試聴・参考のみ」と表示）では、試聴と、「Apple Music で聴く」バッジからストアページを開くことができます。
4. 正しい候補が出ないときは、検索欄の曲名・アーティストを書き換えて再検索します。
5. 「タイアップ / アニソン情報」にタイアップ番組名・種別・ジャンルを入力し、「このトラックに適用」または「アルバム全体に適用」を押します。

## ご注意

- **このアプリは音楽ファイルのタグを直接書き換えます。使用前に必ずバックアップを取ってください。**
- 本ソフトウェアは無保証です（GNU GPL v3 第15条・第16条）。使用によって生じたいかなる損害についても、作者は責任を負いません。
- 取得したジャケット画像などの著作権は、それぞれの権利者に帰属します。ご自身が所有する音楽ファイルの整理（私的利用）の範囲でご利用ください。

## 外部サービスと送信される情報

検索・試聴のときに、以下のサービスへ通信します。送信されるのは**検索に使う曲名とアーティスト名**（および通常の HTTP 通信に含まれる IP アドレス等）だけです。音楽ファイルそのものや、PC 内のその他の情報は送信しません。

| サービス | 用途 | 規約 |
|---|---|---|
| iTunes Search API（Apple） | 曲の検索、試聴音源のストリーミング再生、ストアページへのリンク（試聴音源は保存しません。ジャケット画像は表示のみで、ファイルには埋め込みません） | https://performance-partners.apple.com/search-api |
| MusicBrainz | 曲情報の検索 | https://musicbrainz.org/doc/MusicBrainz_API |
| Cover Art Archive | ジャケット画像の取得 | https://coverartarchive.org/ |

各サービスの提供状況や仕様の変更により、検索機能が使えなくなる場合があります。

## 商標

Apple and Apple Music are trademarks of Apple Inc., registered in the U.S. and other countries.
iTunes は Apple Inc. の商標です。Serato は Serato Limited の商標です。
本ソフトウェアは Apple Inc.、MetaBrainz Foundation（MusicBrainz）、Serato Limited とは無関係で、これらから承認・提携を受けたものではありません。

## ライセンス

DJ Tags は [GNU General Public License v3.0](LICENSE)（またはそれ以降のバージョン）で配布しています。

```
DJ Tags - music tag editor for anime-song DJs
Copyright (C) 2026 たまたらこ

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
```

同梱しているライブラリのライセンスは [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) と `licenses/` フォルダを参照してください。

ソースコード: https://github.com/tamataraco-ops/dj-tags

## ソースから実行・ビルドする

Python 3.14 が必要です。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app.main          # ソースから起動
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\build-release.ps1                              # dist\dj-tags と配布用 zip を作成
```
