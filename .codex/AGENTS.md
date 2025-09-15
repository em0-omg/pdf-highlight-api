# AGENTS.md

このファイルは、このリポジトリでコードを扱う際の AI エージェントへの指示を提供します。

## プロジェクト概要

これは Python 3.13 で構築された記号検出特化型 API プロジェクトです。FastAPI を使用して RESTful API を提供し、図面 PDF ファイルから指定された記号パターンを検出・カウント・ハイライト表示します。このプロジェクトはモダンな Python パッケージ管理に `uv` を使用しています。

### 主な機能

- PDF ファイルのアップロード（マルチパート形式）
- カスタム記号パターンの自動検出（デフォルト: PF100φ/PF150φ 対応）
- 検出位置の座標取得とハイライト表示
- 正確なカウント機能
- 複数ページ対応
- カスタムターゲット画像アップロード対応
- Gemini モデル選択（Pro/Flash）
- PDF プレビュー機能

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

### Docker 環境での実行

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

- **Python バージョン**: 3.13（.python-version で指定）
- **パッケージマネージャー**: uv（pip/poetry のモダンな代替）
- **Web フレームワーク**: FastAPI（高性能な ASYNCIO 対応）
- **PDF 画像変換**: pdf2image + Poppler - 高品質 PDF から画像への変換
- **AI 分析エンジン**: Google Gemini 2.5 Pro/Flash - 最新の多モーダル AI 分析
- **画像処理**: Pillow - Base64 エンコード、リサイズ、フォーマット変換
- **エントリーポイント**: src/main.py に FastAPI アプリケーションが実装されています
- **設定**: pyproject.toml は PEP 518 標準に従います
- **コンテナ化**: Docker と Docker Compose による開発環境

### API エンドポイント

- `GET /` - ヘルスチェック（Gemini API キー状態確認含む）
- `POST /analyze-pdf` - 記号パターン検出・カウント・ハイライト
  - パラメータ: `file` (PDF), `dpi` (解像度), `highlight` (ハイライト有効化), `target_image` (カスタムターゲット), `model` (Gemini モデル)
  - レスポンス: 検出結果、カウント数、座標情報、ハイライト画像

### 環境変数

- `GEMINI_API_KEY` - Google Gemini API key（記号検出機能を使用する場合は必須）

## 開発セットアップ

現在プロジェクトは pyproject.toml に以下の主要な依存関係が定義されています：

- fastapi: 高性能 Web フレームワーク
- uvicorn: ASGI サーバー（非同期処理対応）
- python-multipart: ファイルアップロード処理
- pdf2image: PDF から画像への高品質変換ライブラリ
- pillow: 画像処理・Base64 エンコードライブラリ
- google-generativeai: Google Gemini 2.5 Pro API 連携ライブラリ
- pymupdf: PDF 操作ライブラリ（ハイライト機能実装済み）

現在プロジェクトには以下の開発ツールが追加されています：

- black: コードフォーマッター
- isort: インポート文の整理
- mypy: 型チェック
- pytest: テストフレームワーク
- ruff: リンター（高速な Python linter）

これらの開発ツールは `uv sync` で自動インストールされます。

## プロジェクト構造

```
pdf-highlight-api/
├── src/
│   ├── __init__.py             # パッケージ初期化
│   ├── infrastructure/
│   │   ├── __init__.py         # パッケージ初期化
│   │   └── gemini.py          # Gemini 2.5 Pro/Flash API連携（記号検出特化）
│   ├── assets/
│   │   └── images/
│   │       └── target.png     # デフォルトターゲット画像
│   └── main.py                # 記号検出API エントリーポイント
├── test-pdf-to-image.html     # 記号検出テストインターフェース
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
