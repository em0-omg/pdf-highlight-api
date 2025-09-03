# CLAUDE.md

このファイルは、このリポジトリでコードを扱う際のClaude Code (claude.ai/code)への指示を提供します。

## プロジェクト概要

これは Python 3.13 で構築された PDF ハイライト API プロジェクトで、現在初期開発段階にあります。このプロジェクトはモダンな Python パッケージ管理に `uv` を使用し、PDF ハイライト処理の API 機能を提供するよう設定されています。

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
- **エントリーポイント**: main.py に基本的なアプリケーション構造が含まれています
- **設定**: pyproject.toml は PEP 518 標準に従います

## 開発セットアップ

現在プロジェクトは pyproject.toml に最小限の依存関係が定義されています。機能を追加する際に検討すべき一般的な開発ツール：

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