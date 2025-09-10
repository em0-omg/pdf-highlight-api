# CLAUDE.md

このファイルは、このリポジトリでコードを扱う際のClaude Code (claude.ai/code)への指示を提供します。

## プロジェクト概要

これは Python 3.13 で構築された PF100/PF150 検出特化型 API プロジェクトです。FastAPI を使用してRESTful API を提供し、図面PDFファイルから PF100/PF150 の文言を検出・カウント・ハイライト表示します。このプロジェクトはモダンな Python パッケージ管理に `uv` を使用しています。

### 主な機能
- PDFファイルのアップロード（マルチパート形式）
- PF100/PF150文言の自動検出
- 検出位置の座標取得とハイライト表示
- 正確なカウント機能
- 複数ページ対応

## 必須コマンド

### パッケージ管理
```bash
# 依存関係をインストール/同期
uv sync

# 新しい依存関係を追加
uv add <package-name>

# 開発用依存関係を追加
uv add --dev <package-name>

# アプリケーションを実行
uv run python src/main.py
```

### Docker環境での実行
```bash
# Dockerコンテナのビルドと起動
docker-compose up --build

# バックグラウンドで実行
docker-compose up -d

# コンテナの停止
docker-compose down
```

### 開発ワークフロー
```bash
# コードをフォーマット（blackが利用可能な場合）
black .

# コードをリント（ruffが利用可能な場合） 
ruff check . --fix

# 型チェック（mypyが利用可能な場合）
mypy .

# テストを実行（pytestが利用可能な場合）
pytest
```

**重要**: コードの編集後には必ずリント、フォーマット、型チェックを実行してください。

## アーキテクチャ注記

- **Pythonバージョン**: 3.13（.python-versionで指定）
- **パッケージマネージャー**: uv（pip/poetryのモダンな代替）
- **Webフレームワーク**: FastAPI（高性能なASYNCIO対応）
- **PDF画像変換**: pdf2image + Poppler - 高品質PDFから画像への変換
- **AI分析エンジン**: Google Gemini 2.5 Pro - 最新の多モーダルAI分析
- **画像処理**: Pillow - Base64エンコード、リサイズ、フォーマット変換
- **エントリーポイント**: src/main.py に FastAPI アプリケーションが実装されています
- **設定**: pyproject.toml は PEP 518 標準に従います
- **コンテナ化**: DockerとDocker Composeによる開発環境

### API エンドポイント
- `GET /` - ヘルスチェック（Gemini APIキー状態確認含む）
- `POST /analyze-pdf` - PF100/PF150文言検出・カウント・ハイライト
  - パラメータ: `file` (PDF), `dpi` (解像度), `highlight` (ハイライト有効化), `prompt` (検出指示)
  - レスポンス: 検出結果、カウント数、座標情報、ハイライト画像

### 環境変数
- `GEMINI_API_KEY` - Google Gemini API key（PF100/PF150検出機能を使用する場合は必須）

## 開発セットアップ

現在プロジェクトは pyproject.toml に以下の主要な依存関係が定義されています：
- fastapi: 高性能Webフレームワーク
- uvicorn: ASGIサーバー（非同期処理対応）
- python-multipart: ファイルアップロード処理
- pdf2image: PDFから画像への高品質変換ライブラリ
- pillow: 画像処理・Base64エンコードライブラリ  
- google-generativeai: Google Gemini 2.5 Pro API連携ライブラリ
- pymupdf: PDF操作ライブラリ（将来のハイライト機能用）

現在プロジェクトには以下の開発ツールが追加されています：
- black: コードフォーマッター
- isort: インポート文の整理  
- mypy: 型チェック
- pytest: テストフレームワーク
- ruff: リンター（高速なPython linter）

これらの開発ツールは `uv sync` で自動インストールされます。

## プロジェクト構造

```
pdf-highlight-api/
├── src/
│   ├── infrastructure/
│   │   └── gemini.py          # Gemini 2.5 Pro API連携（PF100/PF150検出特化）
│   └── main.py                # PF100/PF150検出API エントリーポイント
├── test-pdf-to-image.html     # PF100/PF150検出テストインターフェース
├── pyproject.toml             # プロジェクト設定（uv形式）
├── .python-version            # Python 3.13バージョン指定
├── .env.example               # 環境変数のサンプル（GEMINI_API_KEY）
├── Dockerfile                 # Dockerイメージ定義（Python 3.13 + Poppler）
├── docker-compose.yml         # Docker Compose設定
├── .dockerignore              # Docker用の除外ファイル設定
├── CLAUDE.md                  # Claude Code用プロジェクト指示
└── README.md                  # プロジェクト文書
```

プロジェクトが成長するにつれて、`src/` の下に適切なパッケージ構造（ドメイン層、アプリケーション層、インフラ層）でコードを整理することを検討してください。