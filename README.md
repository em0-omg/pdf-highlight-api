# PDF Highlight API

Python 3.13とモダンなツールで構築された、PDF画像変換用のFastAPIベースのREST API。

## 機能

- **PDF画像変換**: Popplerを使用したPDFから画像への高品質変換
- **ファイルアップロード**: multipart/form-data形式でのPDFファイル受信
- **ファイルダウンロード**: 変換済み画像ファイルの即座ダウンロード
- **FastAPIフレームワーク**: 高性能で非同期処理対応のWeb API
- **自動API文書化**: Swagger UI/ReDocによる対話的なAPI文書
- **Docker対応**: コンテナ化された開発・本番環境
- **モダンツール**: `uv`によるPythonパッケージ管理

## 必要要件

- Python 3.13+
- uv（モダンなPythonパッケージマネージャー）
- Docker/Docker Compose（Docker環境で実行する場合）

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

#### ローカル環境
```bash
uv run python src/main.py
```

#### Docker環境
```bash
# 初回起動時（ビルドを含む）
docker-compose up --build

# 2回目以降
docker-compose up

# バックグラウンドで実行
docker-compose up -d

# ログを確認
docker-compose logs -f

# 停止
docker-compose down
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

#### POST `/pdf-to-images`
PDFファイルをすべてのページを画像に変換します。

**リクエスト:**
- Content-Type: `multipart/form-data`
- Body: 
  - `file` (PDF ファイル) - 必須
  - `dpi` (整数) - 解像度（デフォルト: 200）

**レスポンス:**
- 1ページの場合: PNG画像
- 複数ページの場合: ZIPファイル（各ページがPNG画像）

**例:**
```bash
# デフォルトDPI(200)で変換
curl -X POST http://localhost:8000/pdf-to-images \
  -F "file=@example.pdf" \
  --output converted_images.zip

# 高解像度(300 DPI)で変換
curl -X POST http://localhost:8000/pdf-to-images \
  -F "file=@example.pdf" \
  -F "dpi=300" \
  --output high_res_images.zip
```


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

### コード品質

プロジェクトには以下の開発ツールが設定されています：

```bash
# コードフォーマット
black .

# コードリント（高速なPython linter）
ruff check . --fix

# インポート文の整理
isort .

# 型チェック
mypy .

# テスト実行
pytest
```

これらのツールは `uv sync` 実行時に自動的にインストールされます。

## プロジェクト構造

```
pdf-highlight-api/
├── src/
│   └── main.py        # FastAPIアプリケーションエントリーポイント
├── pyproject.toml     # プロジェクト設定と依存関係
├── .python-version    # Python バージョン指定
├── Dockerfile         # Dockerイメージ定義（Python 3.13 + Poppler）
├── docker-compose.yml # Docker Compose設定
├── .dockerignore      # Docker用の除外ファイル設定
├── CLAUDE.md          # AIアシスタント用指示
└── README.md          # プロジェクト文書
```

## 技術スタック

- **フレームワーク**: FastAPI（高性能Web API）
- **ASGIサーバー**: Uvicorn（非同期処理対応）
- **PDF画像変換**: pdf2image + Poppler - 高品質なPDFから画像への変換
- **画像処理**: Pillow - 画像の保存と操作
- **ファイル処理**: python-multipart（ファイルアップロード）
- **コンテナ化**: Docker/Docker Compose
- **Pythonバージョン**: 3.13
- **パッケージマネージャー**: uv
- **設定**: pyproject.toml (PEP 518)

## 今後の開発

PDF画像変換機能は実装済みです。今後の拡張予定:
- PDFハイライト機能の追加（PyMuPDF統合）
- AI解析エンジンとの統合（OCR、テキスト解析、画像認識）
- 画像変換の詳細オプション（フォーマット選択、品質調整など）
- 特定ページの個別変換機能
- 永続化ストレージのためのデータベース統合
- 認証と認可システム
- バッチ処理（複数ファイル同時処理）
- 変換結果のメタデータ出力

## 貢献

1. Python 3.13+がインストールされていることを確認
2. `uv sync`で依存関係をインストール
3. 既存のコードスタイルと規約に従う
4. 新機能にテストを追加
5. 必要に応じてドキュメントを更新

## ライセンス

[ライセンス情報は追加予定]