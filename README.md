# PDF Highlight API

Python 3.13とモダンなツールで構築された、PDFハイライト処理用のFastAPIベースのREST API。

## 機能

- **PDFハイライト処理**: アップロードされたPDFファイルの全ページ中央に黄色いハイライト円を自動追加
- **ファイルアップロード**: multipart/form-data形式でのPDFファイル受信
- **ファイルダウンロード**: 処理済みPDFファイルの即座ダウンロード
- **FastAPIフレームワーク**: 高性能で非同期処理対応のWeb API
- **自動API文書化**: Swagger UI/ReDocによる対話的なAPI文書
- **モダンツール**: `uv`によるPythonパッケージ管理

## 必要要件

- Python 3.13+
- uv（モダンなPythonパッケージマネージャー）

## インストール

1. リポジトリをクローン:
```bash
git clone <repository-url>
cd pdf-highlight-api
```

2. 依存関係をインストール:
```bash
uv sync
```

## 使用方法

### APIサーバーの起動

```bash
uv run main.py
```

APIは `http://localhost:8000` でアクセス可能です。

### API文書

サーバー起動後、以下にアクセスできます:
- 対話的なAPI文書 (Swagger UI): `http://localhost:8000/docs`
- 代替API文書 (ReDoc): `http://localhost:8000/redoc`

### APIエンドポイント

#### GET `/`
APIのヘルスチェック用エンドポイント。

**レスポンス:**
```json
{
  "message": "PDF Highlight API is running"
}
```

**例:**
```bash
curl http://localhost:8000/
```

#### POST `/highlight-pdf`
PDFファイルをアップロードして、全ページの中央にハイライト円を追加します。

**リクエスト:**
- Content-Type: `multipart/form-data`
- Body: `file` (PDF ファイル)

**レスポンス:**
- Content-Type: `application/pdf`
- ハイライトが追加されたPDFファイルが返されます

**例:**
```bash
# cURLでPDFファイルをアップロード
curl -X POST http://localhost:8000/highlight-pdf \
  -F "file=@example.pdf" \
  --output highlighted_example.pdf

# Swagger UIを使用する場合
# http://localhost:8000/docs にアクセスして
# /highlight-pdf エンドポイントからファイルをアップロード
```

**機能詳細:**
- 受信したPDFファイルの全ページを処理
- 各ページの中央（width/2, height/2）に半径20の黄色いハイライト円を追加
- 処理済みPDFを `highlighted_[元のファイル名]` として返却

## 開発

### パッケージ管理

```bash
# 新しい依存関係を追加
uv add <package-name>

# 開発用依存関係を追加
uv add --dev <package-name>

# 依存関係を同期
uv sync
```

### コード品質（ツールが利用可能な場合）

```bash
# コードフォーマット
black .

# コードリント
ruff check . --fix

# 型チェック
mypy .

# テスト実行
pytest
```

## プロジェクト構造

```
pdf-highlight-api/
├── main.py            # FastAPIアプリケーションエントリーポイント
├── pyproject.toml     # プロジェクト設定と依存関係
├── .python-version    # Python バージョン指定
├── CLAUDE.md          # AIアシスタント用指示
└── README.md          # プロジェクト文書
```

## 技術スタック

- **フレームワーク**: FastAPI（高性能Web API）
- **ASGIサーバー**: Uvicorn（非同期処理対応）
- **PDF処理**: PyMuPDF (fitz) - PDF読み書きとハイライト機能
- **ファイル処理**: python-multipart（ファイルアップロード）
- **Pythonバージョン**: 3.13
- **パッケージマネージャー**: uv
- **設定**: pyproject.toml (PEP 518)

## 今後の開発

基本的なPDFハイライト機能は実装済みです。今後の拡張予定:
- ハイライトの位置、色、サイズのカスタマイズ
- 複数のハイライトマーク（矩形、テキスト）の追加
- PDFハイライト情報の抽出とメタデータ出力
- 永続化ストレージのためのデータベース統合
- 認証と認可
- バッチ処理（複数ファイル同時処理）

## 貢献

1. Python 3.13+がインストールされていることを確認
2. `uv sync`で依存関係をインストール
3. 既存のコードスタイルと規約に従う
4. 新機能にテストを追加
5. 必要に応じてドキュメントを更新

## ライセンス

[ライセンス情報は追加予定]