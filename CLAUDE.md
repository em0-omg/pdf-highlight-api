# CLAUDE.md

このファイルは、このリポジトリでコードを扱う際のClaude Code (claude.ai/code)への指示を提供します。

## プロジェクト概要

これは Python 3.13 で構築された PDF ハイライト API プロジェクトです。FastAPI を使用してRESTful API を提供し、PyMuPDF (fitz) を使用してPDFファイルの中央にハイライトマークを追加する機能を実装しています。このプロジェクトはモダンな Python パッケージ管理に `uv` を使用しています。

### 主な機能
- PDFファイルのアップロード
- PDF の全ページ中央にハイライト円を自動追加
- ハイライト済みPDFファイルのダウンロード

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
uv run main.py
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

## アーキテクチャ注記

- **Pythonバージョン**: 3.13（.python-versionで指定）
- **パッケージマネージャー**: uv（pip/poetryのモダンな代替）
- **Webフレームワーク**: FastAPI（高性能なASYNCIO対応）
- **PDF処理**: PyMuPDF (fitz) - PDFの読み書きとハイライト機能
- **エントリーポイント**: main.py に FastAPI アプリケーションが実装されています
- **設定**: pyproject.toml は PEP 518 標準に従います

### API エンドポイント
- `GET /` - ヘルスチェック
- `POST /highlight-pdf` - PDFファイルの中央にハイライトを追加

## 開発セットアップ

現在プロジェクトは pyproject.toml に以下の主要な依存関係が定義されています：
- fastapi: Webフレームワーク
- uvicorn: ASGIサーバー  
- pymupdf: PDF処理ライブラリ
- python-multipart: ファイルアップロード処理

機能を追加する際に検討すべき一般的な開発ツール：

```bash
uv add --dev pytest black isort mypy ruff
```

## プロジェクト構造

```
pdf-highlight-api/
├── main.py            # アプリケーションエントリーポイント
├── pyproject.toml     # プロジェクト設定
└── .python-version    # Python バージョン指定
```

プロジェクトが成長するにつれて、`src/pdf_highlight_api/` の下に適切なパッケージ構造でコードを整理することを検討してください。