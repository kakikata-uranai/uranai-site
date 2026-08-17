# 書き方占い サイト

`Uranai` プロジェクトで生成した記事（`note_generator.py` の出力）を
静的サイト化して GitHub Pages で公開するリポジトリです。

## 構成

```
uranai-site/
├── articles/            記事本体（note_{漢字}_{番号}.md）
├── data/
│   ├── kakikuse.json     漢字・パターンのメタデータ
│   └── links.json        アフィリエイトリンク設定（★ここを編集する）
├── assets/images/        漢字イメージ画像
├── scripts/
│   └── build_site.py     静的サイトビルドスクリプト（標準ライブラリのみ）
├── .github/workflows/
│   └── deploy.yml         push時に自動ビルド・GitHub Pagesへ自動デプロイ
└── docs/                  ビルド生成物（.gitignore対象・コミット不要）
```

## アフィリエイトリンクの反映方法

`data/links.json` の2つのURLを、ASPで発行された実際のリンクに書き換えて
push するだけです。サイト内のすべてのCTAボタンに自動反映されます。

```json
{
  "affiliate_link": "https://実際のASPリンク",
  "omikuji_link": "https://実際のASPリンク"
}
```

## ローカルでの確認方法

```bash
python scripts/build_site.py
cd docs
python -m http.server 8000
# ブラウザで http://localhost:8000 を開く
```

## デプロイの仕組み

`main` ブランチに push すると、GitHub Actions が自動的に
`scripts/build_site.py` を実行して `docs/` を生成し、GitHub Pages に
デプロイします。手動でのビルド・アップロードは不要です。

初回のみ、リポジトリの **Settings → Pages → Build and deployment → Source**
を「**GitHub Actions**」に設定してください。

## 記事を追加する場合

1. `Uranai` プロジェクト側で `note_generator.py` を使って新しい記事
   （例: Graphologyパターン）を生成する
2. 生成された `note_{漢字}_{番号}.md` を `articles/` にコピー
3. `data/kakikuse.json` に該当漢字・パターンのメタデータを追記
4. push すれば自動的にサイトへ反映される

## 今後の拡張候補（未着手）

- 週次でGemini APIを呼び直し「今週の運勢」を自動更新するワークフロー
  （`GOOGLE_API_KEY` をリポジトリの Secrets に登録すれば実装可能）
- Graphologyパターン（筆跡全体・アルファベット）の追加
- 独自ドメインの設定
