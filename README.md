# PDF Analysis API

Python 3.13とモダンなツールで構築された、PDF分析・画像変換用のFastAPIベースのREST API。Google Gemini 2.5 Pro による高度なAI文書分析機能を提供します。

## 機能

- **AI文書分析**: Google Gemini 2.5 Pro による包括的なPDF内容分析
- **PDF画像変換**: Popplerを使用したPDFから画像への高品質変換
- **リアルタイムプレビュー**: Base64エンコード画像の即座表示
- **複数ページ対応**: 大容量PDFの並列処理と個別ページ分析
- **インタラクティブUI**: test-pdf-to-image.html によるWebインターフェース
- **ファイルアップロード**: multipart/form-data形式でのPDFファイル受信
- **FastAPIフレームワーク**: 高性能で非同期処理対応のWeb API
- **自動API文書化**: Swagger UI/ReDocによる対話的なAPI文書
- **Docker対応**: コンテナ化された開発・本番環境
- **モダンツール**: `uv`によるPythonパッケージ管理

## 必要要件

- Python 3.13+
- uv（モダンなPythonパッケージマネージャー）
- Docker/Docker Compose（Docker環境で実行する場合）
- Google Gemini API Key（AI分析機能を使用する場合）
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
  "message": "PDF Analysis API is running",
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
PDFファイルを画像に変換し、Gemini AIで包括的に分析します。

**リクエスト:**
- Content-Type: `multipart/form-data`
- Body: 
  - `file` (PDF ファイル) - 必須
- Query Parameters:
  - `dpi` (整数) - 画像解像度（デフォルト: 200）
  - `prompt` (文字列) - 分析指示（デフォルト: "この文書について説明してください。"）

**レスポンス:**
```json
{
  "filename": "example.pdf",
  "total_pages": 3,
  "analysis": "文書の詳細な分析結果...",
  "images": [
    {
      "page": 1,
      "image_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgA..."
    }
  ],
  "prompt": "この文書について説明してください。",
  "dpi": 200
}
```

**例:**
```bash
# 基本的な分析
curl -X POST "http://localhost:8000/analyze-pdf" \
  -F "file=@example.pdf"

# カスタムプロンプトで分析
curl -X POST "http://localhost:8000/analyze-pdf?prompt=この文書の要点を3つ挙げてください&dpi=300" \
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
│   ├── infrastructure/
│   │   └── gemini.py          # Gemini 2.5 Pro API連携サービス
│   └── main.py                # FastAPIアプリケーションエントリーポイント
├── test-pdf-to-image.html     # インタラクティブWebテストインターフェース
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
- **AI分析エンジン**: Google Gemini 2.5 Pro（最新の多モーダルAI）
- **PDF画像変換**: pdf2image + Poppler（高品質なPDFから画像への変換）
- **画像処理**: Pillow（Base64エンコード、リサイズ、フォーマット変換）
- **ファイル処理**: python-multipart（ファイルアップロード）
- **コンテナ化**: Docker/Docker Compose
- **Pythonバージョン**: 3.13
- **パッケージマネージャー**: uv
- **設定**: pyproject.toml (PEP 518)

## セットアップ手順

### 環境変数の設定
AI分析機能を使用するには、Google Gemini API Keyが必要です：

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
`test-pdf-to-image.html` を開いてインタラクティブなWebインターフェースを使用できます：

1. APIサーバーを起動
2. ブラウザで `test-pdf-to-image.html` を開く
3. PDFファイルをドラッグ&ドロップまたは選択
4. 分析プロンプトとDPI設定を調整
5. 「PDFを分析」ボタンをクリック

## 今後の開発

PDF分析機能は実装済みです。今後の拡張予定:
- PDFハイライト機能の追加（PyMuPDF統合）
- 複数分析タイプ（要約、重要ポイント抽出、テキスト抽出）
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