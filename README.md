# PDF Highlight API

Python 3.13とモダンなツールで構築された、PDFハイライト処理用のFastAPIベースのREST API。

## 機能

- 高性能API用のFastAPIウェブフレームワーク
- RESTful APIエンドポイント
- Swagger UIによる自動API文書化
- `uv`によるモダンなPythonパッケージ管理

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
シンプルなハローワールドメッセージを返します。

**レスポンス:**
```json
{
  "message": "Hello World"
}
```

**例:**
```bash
curl http://localhost:8000/
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

- **フレームワーク**: FastAPI
- **ASGIサーバー**: Uvicorn
- **Pythonバージョン**: 3.13
- **パッケージマネージャー**: uv
- **設定**: pyproject.toml (PEP 518)

## 今後の開発

このプロジェクトは初期開発段階です。予定されている機能:
- PDFハイライトの抽出と管理
- 永続化ストレージのためのデータベース統合
- 認証と認可
- PDF操作のための追加APIエンドポイント

## 貢献

1. Python 3.13+がインストールされていることを確認
2. `uv sync`で依存関係をインストール
3. 既存のコードスタイルと規約に従う
4. 新機能にテストを追加
5. 必要に応じてドキュメントを更新

## ライセンス

[ライセンス情報は追加予定]