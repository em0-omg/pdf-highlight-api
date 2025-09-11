from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pdf2image import convert_from_bytes
import uvicorn
import io
import base64
import os
from src.infrastructure.gemini import GeminiImageAnalyzer

app = FastAPI(
    title="図面PDF解析API",
    version="0.2.0",
    description="図面PDFを分析し、PF100/PF150の文言とポイント数をカウントする特化型API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gemini API Key の状態を確認
gemini_api_key = os.getenv("GEMINI_API_KEY")
gemini_analyzer = None
gemini_available = False

if gemini_api_key:
    try:
        gemini_analyzer = GeminiImageAnalyzer()
        gemini_available = True
        print("✅ Gemini API Key found. Analysis features are available.")
    except Exception as e:
        print(f"❌ Error initializing Gemini: {e}")
        print("🔧 Please check your GEMINI_API_KEY.")
else:
    print("⚠️  GEMINI_API_KEY not found.")
    print("🔧 Please set GEMINI_API_KEY in your .env file to enable analysis features.")
    print("📝 Get your API key from: https://makersuite.google.com/app/apikey")


@app.get("/")
async def hello_world():
    return {
        "message": "図面PDF解析API is running",
        "description": "図面PDFを分析し、PF100/PF150の文言とポイント数をカウントする特化型API",
        "gemini_available": gemini_available,
        "status": "✅ Ready" if gemini_available else "⚠️ Gemini API Key required",
        "setup_help": (
            "Set GEMINI_API_KEY in .env file" if not gemini_available else None
        ),
        "features": [
            "PF100/PF150文言検出",
            "記号位置座標検出",
            "自動カウント",
            "ハイライト表示",
        ],
    }


@app.post("/analyze-pdf")
async def analyze_pdf(
    file: UploadFile = File(...),
    dpi: int = 200,
    highlight: bool = Query(True, description="ハイライト機能を有効にするかどうか"),
    keywords: str = Query("PF100,PF150", description="検出したいキーワード（カンマ区切り）※矢印で図面記号を指し示しているもののみ検出"),
    model: str = Query("gemini-2.5-pro", description="使用するGeminiモデル（gemini-2.5-pro または gemini-2.5-flash）"),
):
    """
    PDFファイル内の指定キーワードをハイライト表示する（改良された高精度検出）

    Parameters:
    - file: PDFファイル（アップロード）
    - dpi: 画像変換解像度（デフォルト200）
    - highlight: ハイライト機能有効化フラグ（デフォルトTrue）
    - keywords: 検出したいキーワード（カンマ区切り）

    Returns:
    - 座標情報（積極的検出 + フォールバック機能）
    - ハイライト付き画像（highlight=Trueの場合）
    """
    print(f"📄 ハイライト処理開始: {file.filename}")

    if not gemini_available:
        print("❌ Gemini API不可: APIキーが設定されていません")
        raise HTTPException(
            status_code=503,
            detail="Gemini analysis service is not available. Please set GEMINI_API_KEY in your .env file. Get your API key from: https://makersuite.google.com/app/apikey",
        )

    if not file.filename or not file.filename.endswith(".pdf"):
        print(f"❌ 無効なファイル形式: {file.filename}")
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        print("📖 PDFファイルを読み込み中...")
        pdf_bytes = await file.read()

        print(f"🖼️  PDFを画像に変換中... (DPI: {dpi})")
        images = convert_from_bytes(pdf_bytes, dpi=dpi)
        print(f"✅ 変換完了: {len(images)}ページの画像を生成")

        # 画像プレビューデータを作成
        print("🎨 元画像プレビューデータを作成中...")
        preview_images = _create_image_previews(images)
        print("✅ 元画像プレビューデータ作成完了")

        # 座標検出とハイライト処理
        highlighted_images = []
        all_detection_data = []
        keyword_list = [kw.strip() for kw in keywords.split(",") if kw.strip()]

        if highlight and keyword_list:
            print(f"🎯 文言座標検出を開始: {keyword_list} (積極的検出モード)")
            print(f"🤖 使用モデル: {model}")
            
            # 指定されたモデルでanalyzerを作成
            try:
                model_analyzer = GeminiImageAnalyzer(model_name=model)
            except Exception as e:
                print(f"❌ モデル初期化エラー: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to initialize model {model}: {str(e)}")
            
            for i, image in enumerate(images):
                print(f"📍 ページ{i+1}: 文言検出中...")
                if model_analyzer:
                    detection_data = (
                        await model_analyzer.analyze_image_with_coordinates(
                            image, keyword_list
                        )
                    )
                    all_detection_data.append(detection_data)

                    if "error" not in detection_data:
                        print(f"🎨 ページ{i+1}: ハイライト描画中...")
                        highlighted_image = model_analyzer.create_highlighted_image(
                            image, detection_data
                        )

                        # ハイライト済み画像をBase64エンコード
                        img_buffer = io.BytesIO()
                        highlighted_image.save(img_buffer, format="PNG")
                        img_buffer.seek(0)
                        img_base64 = base64.b64encode(img_buffer.getvalue()).decode(
                            "utf-8"
                        )

                        highlighted_images.append(
                            {
                                "page": i + 1,
                                "image_data": f"data:image/png;base64,{img_base64}",
                                "detections": detection_data.get("detections", []),
                                "summary": detection_data.get("summary", {}),
                            }
                        )
                        print(f"✅ ページ{i+1}: ハイライト完了")
                    else:
                        print(
                            f"⚠️ ページ{i+1}: 座標検出エラー - {detection_data.get('error', '不明なエラー')}"
                        )
                        highlighted_images.append(
                            {
                                "page": i + 1,
                                "error": detection_data.get(
                                    "error", "座標検出に失敗しました"
                                ),
                            }
                        )
                else:
                    print(f"⚠️ ページ{i+1}: Gemini分析機能を利用できません")
                    highlighted_images.append(
                        {"page": i + 1, "error": "Gemini分析機能を利用できません"}
                    )
            print("✅ 全ページのハイライト処理完了")


        print(f"🎉 ハイライト処理完了: {file.filename}")

        response_data = {
            "filename": file.filename,
            "total_pages": len(images),
            "images": preview_images,
            "keywords": keyword_list,
            "dpi": dpi,
            "highlight_enabled": highlight,
            "analysis_type": "文言ハイライト特化型API",
        }

        # ハイライトデータの追加
        response_data["highlighted_images"] = highlighted_images
        response_data["detection_data"] = all_detection_data

        return response_data

    except Exception as e:
        print(f"❌ PDF処理エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


def _create_image_previews(images: list) -> list:
    """
    画像のBase64エンコードプレビューを作成
    """
    preview_images = []
    for i, image in enumerate(images):
        img_buffer = io.BytesIO()
        image.save(img_buffer, format="PNG")
        img_buffer.seek(0)

        img_base64 = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
        preview_images.append(
            {"page": i + 1, "image_data": f"data:image/png;base64,{img_base64}"}
        )

    return preview_images




if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
