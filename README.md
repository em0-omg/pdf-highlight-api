# 記号検出API

Python 3.13とモダンなツールで構築された、PDF内記号パターン検出用のFastAPIベースのREST API。Google Gemini 2.5 Pro/Flash による高度なAI記号認識機能を提供します。

## 機能

- **AI記号認識**: Google Gemini 2.5 Pro/Flash による高精度記号パターン検出
- **カスタムターゲット**: 任意の記号画像をアップロードして検出対象を指定
- **PDF画像変換**: Popplerを使用したPDFから画像への高品質変換
- **リアルタイムプレビュー**: PDFプレビューとBase64エンコード画像の即座表示
- **ハイライト機能**: 検出した記号を矩形ハイライトで表示
- **複数ページ対応**: 大容量PDFの並列処理と個別ページ分析
- **インタラクティブUI**: モーダル表示、キーボードナビゲーション対応のWebインターフェース
- **ファイルアップロード**: ドラッグ&ドロップ対応のMultipart/form-dataアップロード
- **モデル選択**: Gemini ProとFlashの選択可能
- **FastAPIフレームワーク**: 高性能で非同期処理対応のWeb API
- **自動API文書化**: Swagger UI/ReDocによる対話的なAPI文書
- **Docker対応**: コンテナ化された開発・本番環境
- **モダンツール**: `uv`によるPythonパッケージ管理

## 必要要件

- Python 3.13+
- uv（モダンなPythonパッケージマネージャー）
- Docker/Docker Compose（Docker環境で実行する場合）
- Google Gemini API Key（AI記号認識機能を使用する場合）
- Poppler（PDF画像変換ライブラリ - Dockerに含まれています）

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
APIのヘルスチェック用エンドポイント。Gemini API の利用可能性も確認できます。

**レスポンス:**
```json
{
  "message": "Symbol Detection API is running",
  "gemini_available": true,
  "status": "✅ Ready",
  "setup_help": null
}
```

**例:**
```bash
curl http://localhost:8000/
```

#### POST `/analyze-pdf`
PDFファイルを画像に変換し、Gemini AIで記号パターンを検出します。

**リクエスト:**
- Content-Type: `multipart/form-data`
- Body: 
  - `file` (PDF ファイル) - 必須
  - `target_image` (ターゲット画像 ファイル) - オプション
- Query Parameters:
  - `dpi` (整数) - 画像解像度（デフォルト: 200）
  - `highlight` (ブール値) - ハイライト有効化（デフォルト: true）
  - `model` (文字列) - Geminiモデル選択（デフォルト: "gemini-2.5-pro"）

**レスポンス:**
```json
{
  "filename": "example.pdf",
  "total_pages": 3,
  "total_detections": 5,
  "analysis_summary": "記号検出結果の詳細...",
  "pages": [
    {
      "page": 1,
      "detections": 2,
      "coordinates": [
        {"x1": 100, "y1": 150, "x2": 200, "y2": 250, "confidence": 0.95}
      ],
      "original_image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgA...",
      "highlighted_image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgA..."
    }
  ],
  "model_used": "gemini-2.5-pro",
  "dpi": 200
}
```

補足: 読み込み確認のため、ターゲット画像の特徴説明が `target_image_overview` に含まれます。

```json
{
  "target_image_overview": {
    "source": "custom | default",
    "width": 128,
    "height": 128,
    "model": "gemini-2.5-pro",
    "description": "・円形の外枠 … のような特徴\n・中央に十字 … など"
  }
}
```

**例:**
```bash
# 基本的な記号検出
curl -X POST "http://localhost:8000/analyze-pdf" \
  -F "file=@example.pdf"

# カスタムターゲットで検出
curl -X POST "http://localhost:8000/analyze-pdf?dpi=300&model=gemini-2.5-flash" \
  -F "file=@example.pdf" \
  -F "target_image=@custom_symbol.png"

# ハイライトなしで検出のみ
curl -X POST "http://localhost:8000/analyze-pdf?highlight=false" \
  -F "file=@example.pdf"
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
│   ├── __init__.py             # パッケージ初期化
│   ├── infrastructure/
│   │   ├── __init__.py         # パッケージ初期化
│   │   └── gemini.py          # Gemini 2.5 Pro/Flash API連携サービス
│   ├── assets/
│   │   └── images/
│   │       └── target.png     # デフォルトターゲット画像
│   └── main.py                # FastAPIアプリケーションエントリーポイント
├── test-pdf-to-image.html     # 記号検出インタラクティブWebインターフェース
├── pyproject.toml             # プロジェクト設定と依存関係（uv形式）
├── .python-version            # Python 3.13バージョン指定
├── .env.example               # 環境変数のサンプル（GEMINI_API_KEY）
├── Dockerfile                 # Dockerイメージ定義（Python 3.13 + Poppler）
├── docker-compose.yml         # Docker Compose設定
├── .dockerignore              # Docker用の除外ファイル設定
├── CLAUDE.md                  # Claude Code用プロジェクト指示
└── README.md                  # プロジェクト文書
```

## 技術スタック

- **フレームワーク**: FastAPI（高性能Web API）
- **ASGIサーバー**: Uvicorn（非同期処理対応）
- **AI分析エンジン**: Google Gemini 2.5 Pro/Flash（最新の多モーダルAI）
- **PDF画像変換**: pdf2image + Poppler（高品質なPDFから画像への変換）
- **画像処理**: Pillow（Base64エンコード、リサイズ、フォーマット変換）
- **ファイル処理**: python-multipart（ファイルアップロード）
- **コンテナ化**: Docker/Docker Compose
- **Pythonバージョン**: 3.13
- **パッケージマネージャー**: uv
- **設定**: pyproject.toml (PEP 518)

## セットアップ手順

### 環境変数の設定
AI記号認識機能を使用するには、Google Gemini API Keyが必要です：

1. `.env.example` を `.env` にコピー:
```bash
cp .env.example .env
```

2. `.env` ファイルに API キーを設定:
```bash
GEMINI_API_KEY=your_api_key_here
```

3. API キーの取得: [Google AI Studio](https://makersuite.google.com/app/apikey)

### Webインターフェースの使用
`test-pdf-to-image.html` を開いて記号検出用インタラクティブWebインターフェースを使用できます：

1. APIサーバーを起動
2. ブラウザで `test-pdf-to-image.html` を開く
3. PDFファイルをドラッグ&ドロップまたは選択
4. オプションでカスタムターゲット画像をアップロード
5. Geminiモデル、DPI設定、ハイライトオプションを調整
6. 「記号を検出」ボタンをクリック
7. PDFプレビューで内容を確認後、検出を実行

## 今後の開発

記号検出機能は実装済みです。今後の拡張予定:
- 文字認識ベースのテキスト検出（OCR連携）
- 複数記号パターンの同時検出
- 検出結果のエクスポート機能（JSON, CSV, PDFレポート）
- 特定ページの個別処理機能
- 永続化ストレージのためのデータベース統合
- 認証と認可システム
- バッチ処理（複数ファイル同時処理）
- 連続処理のためのキューシステム
- リアルタイムストリーミング処理

## 貢献

1. Python 3.13+がインストールされていることを確認
2. `uv sync`で依存関係をインストール
3. 既存のコードスタイルと規約に従う
4. 新機能にテストを追加
5. 必要に応じてドキュメントを更新

## ライセンス

[ライセンス情報は追加予定]
