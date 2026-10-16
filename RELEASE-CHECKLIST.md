# 公開前チェックリスト（配布する人向け・配布物には含まれません）

## 公開前に必ずやること

- [ ] `app/about.py` の `AUTHOR`（ハンドルネーム）と `REPO_URL`（公開リポジトリの URL）を書き換える
- [ ] `README.md` の `YOUR_HANDLE` と `YOUR_ACCOUNT` を同じ値に書き換える
  （`build-release.ps1` は、仮の値が残っているとビルドを止めます）
- [ ] GitHub に公開リポジトリを作り、このフォルダの内容を push する（`LICENSE` があれば GitHub が GPL-3.0 と認識します）
- [x] iTunes Search API の規約を確認し、iTunes の結果は「試聴・ストアへのリンク・参考表示」だけに使うよう変更済み
  （ジャケットは埋め込まない／試聴は保存しない／「provided courtesy of iTunes」を表示）
  https://performance-partners.apple.com/search-api
- [ ] 規約は試聴の近くに**公式のストアバッジ**（購入ページへのリンク）を置くよう求めている。
  今はテキストのリンクボタン（「iTunes / Apple Music で見る」）なので、厳密に合わせるなら
  Apple の Marketing Tools（https://tools.applemediaservices.com/）から公式バッジを入手し、
  Apple のガイドラインに同意したうえで、このボタンをバッジ画像に差し替える
- [ ] `.\build-release.ps1` でビルドし、`dist\dj-tags-<version>-win64.zip` を GitHub の Release に添付する

## 公開したあとも続く義務

- GPL / LGPL の条件として、**配布したバージョンのソースコードを入手できる状態を保つ**必要があります。
  - DJ Tags 本体：リポジトリにタグ（例：`v0.1.0`）を付けておけば、その版のソースを示せます。
  - Qt / FFmpeg：`THIRD-PARTY-NOTICES.md` では公式の配布サイトを案内しています。そこで入手できなくなった場合に
    提供を求められたら、応じる必要があります。不安なら、使ったバージョンのソースアーカイブを Release に一緒に置いておくと確実です。
- バージョンを上げるときは `app/about.py` の `VERSION` を更新し、ライブラリを更新した場合は
  `THIRD-PARTY-NOTICES.md` のバージョン表と `licenses/` も合わせて更新してください。

## 任意（やると親切）

- 各ソースファイルの先頭に GPL のライセンスヘッダーを入れる
- コード署名をして SmartScreen の警告を減らす（有料の証明書が必要）
