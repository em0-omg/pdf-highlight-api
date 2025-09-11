from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pdf2image import convert_from_bytes
import uvicorn
import io
import base64
import os
import re
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
    prompt: str = Query(
        "この図面上で「PF100φ」と「PF150φ」の文言を特定し、正確にカウントしてください。\n"
        "他の記号や文字は無視し、PF100φ、PF150φのみに特化して検出してください。\n"
        "検出結果は以下の形式で回答してください：\n"
        "- PF100φ: X箇所\n"
        "- PF150φ: Y箇所",
        description="PF100φ/PF150φ文言検出用プロンプト",
    ),
):
    """
    図面PDFファイルでPF100φ/PF150φ文言を検出し、カウント・座標取得を実行する

    Parameters:
    - file: PDFファイル（アップロード）
    - dpi: 画像変換解像度（デフォルト200）
    - highlight: ハイライト機能有効化フラグ（デフォルトTrue）
    - prompt: PF100φ/PF150φ文言検出特化プロンプト

    Returns:
    - PF100φ/PF150φ文言検出結果
    - 正確なカウント数と座標情報
    - ハイライト付き画像（highlight=Trueの場合）
    """
    print(f"📄 PF100φ/PF150φ文言検出開始: {file.filename}")

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

        if highlight:
            print("🎯 PF100φ/PF150φ文言座標検出を開始...")
            for i, image in enumerate(images):
                print(f"📍 ページ{i+1}: PF100φ/PF150φ文言検出中...")
                if gemini_analyzer:
                    detection_data = (
                        await gemini_analyzer.analyze_image_with_coordinates(
                            image, ["PF100φ", "PF150φ"]
                        )
                    )
                    all_detection_data.append(detection_data)

                    if "error" not in detection_data:
                        print(f"🎨 ページ{i+1}: ハイライト描画中...")
                        highlighted_image = gemini_analyzer.create_highlighted_image(
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

        # PF100φ/PF150φ文言検出分析を実行
        print("🤖 PF100φ/PF150φ文言検出分析を開始...")
        if gemini_analyzer:
            if len(images) > 1:
                print(
                    f"📚 複数ページ分析: {len(images)}ページでPF100φ/PF150φ文言を検出中..."
                )
                analysis_results = await gemini_analyzer.analyze_images(images, prompt)
                overall_analysis = (
                    f"全{len(images)}ページのPF100φ/PF150φ検出結果:\n"
                    + "\n\n".join(
                        [
                            f"ページ{i+1}: {result}"
                            for i, result in enumerate(analysis_results)
                        ]
                    )
                )
                print("✅ 複数ページPF100φ/PF150φ検出完了")
            else:
                print("📄 単一ページPF100φ/PF150φ検出中...")
                overall_analysis = await gemini_analyzer.analyze_image(
                    images[0], prompt
                )
                print("✅ 単一ページPF100φ/PF150φ検出完了")
        else:
            overall_analysis = "Gemini分析機能は利用できません。"

        # PF100φ/PF150φのカウント結果を抽出（座標データとテキスト分析を統合）
        pf_counts = _extract_pf_counts(overall_analysis)

        # 座標データからPF100φ/PF150φの正確なカウントを取得
        if all_detection_data:
            coordinate_counts = {"PF100φ": 0, "PF150φ": 0, "total_detections": 0}
            for detection_data in all_detection_data:
                if "summary" in detection_data:
                    coordinate_counts["PF100φ"] += detection_data["summary"].get(
                        "pf100_count", 0
                    )
                    coordinate_counts["PF150φ"] += detection_data["summary"].get(
                        "pf150_count", 0
                    )
                    coordinate_counts["total_detections"] += detection_data[
                        "summary"
                    ].get("total_detections", 0)

            # 座標ベースのPF100φ/PF150φカウントをメインに使用
            pf_counts["coordinate_based"] = coordinate_counts

        print(f"🎉 PF100φ/PF150φ文言検出完了: {file.filename}")

        response_data = {
            "filename": file.filename,
            "total_pages": len(images),
            "analysis": overall_analysis,
            "pf_counts": pf_counts,
            "images": preview_images,
            "prompt": prompt,
            "dpi": dpi,
            "highlight_enabled": highlight,
            "analysis_type": "PF100φ/PF150φ文言検出特化型API",
        }

        # ハイライト機能が有効な場合のみ追加
        if highlight:
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


def _extract_pf_counts(analysis_text: str) -> dict:
    """
    AI分析結果からPF100φとPF150φのカウント数を抽出
    """
    pf_counts = {
        "PF100φ": 0,
        "PF150φ": 0,
        "extraction_details": {"found_pf100_patterns": [], "found_pf150_patterns": []},
    }

    try:
        # PF100φのパターンを検索
        pf100_patterns = [
            r"PF100φ[:\s]*(\d+)[箇個ヶ]所",
            r"PF100Φ[:\s]*(\d+)[箇個ヶ]所",
            r"PF100φ[:\s]*(\d+)箇所",
            r"PF100Φ[:\s]*(\d+)箇所",
            r"PF100φ[:\s]*(\d+)個",
            r"PF100Φ[:\s]*(\d+)個",
            r"PF100φ[:\s]*(\d+)ヶ所",
            r"PF100Φ[:\s]*(\d+)ヶ所",
            r"PF100φ[:\s]*(\d+)\s*箇所",
            r"PF100Φ[:\s]*(\d+)\s*箇所",
            r"「?PF100φ」?[:\s]*(\d+)",
            r"「?PF100Φ」?[:\s]*(\d+)",
            r"PF100φ.*?(\d+)箇所",
            r"PF100Φ.*?(\d+)箇所",
            r"PF100φ.*?(\d+)個所",
            r"PF100Φ.*?(\d+)個所",
        ]

        # PF150φのパターンを検索
        pf150_patterns = [
            r"PF150φ[:\s]*(\d+)[箇個ヶ]所",
            r"PF150Φ[:\s]*(\d+)[箇個ヶ]所",
            r"PF150φ[:\s]*(\d+)箇所",
            r"PF150Φ[:\s]*(\d+)箇所",
            r"PF150φ[:\s]*(\d+)個",
            r"PF150Φ[:\s]*(\d+)個",
            r"PF150φ[:\s]*(\d+)ヶ所",
            r"PF150Φ[:\s]*(\d+)ヶ所",
            r"PF150φ[:\s]*(\d+)\s*箇所",
            r"PF150Φ[:\s]*(\d+)\s*箇所",
            r"「?PF150φ」?[:\s]*(\d+)",
            r"「?PF150Φ」?[:\s]*(\d+)",
            r"PF150φ.*?(\d+)箇所",
            r"PF150Φ.*?(\d+)箇所",
            r"PF150φ.*?(\d+)個所",
            r"PF150Φ.*?(\d+)個所",
        ]

        # PF100φを検索
        for pattern in pf100_patterns:
            matches = re.findall(pattern, analysis_text, re.IGNORECASE)
            if matches:
                pf_counts["PF100φ"] = int(matches[0])
                extraction_details = pf_counts.get("extraction_details")
                if isinstance(extraction_details, dict):
                    extraction_details["found_pf100_patterns"].append(
                        {"pattern": pattern, "count": int(matches[0])}
                    )
                break

        # PF150φを検索
        for pattern in pf150_patterns:
            matches = re.findall(pattern, analysis_text, re.IGNORECASE)
            if matches:
                pf_counts["PF150φ"] = int(matches[0])
                extraction_details = pf_counts.get("extraction_details")
                if isinstance(extraction_details, dict):
                    extraction_details["found_pf150_patterns"].append(
                        {"pattern": pattern, "count": int(matches[0])}
                    )
                break

        # 単純な文字列検索もバックアップとして実行（PF100φ/PF150φのみ）
        if pf_counts["PF100φ"] == 0:
            pf100_mentions = len(re.findall(r"PF100[φΦ]", analysis_text, re.IGNORECASE))
            if pf100_mentions > 0:
                extraction_details = pf_counts.get("extraction_details")
                if isinstance(extraction_details, dict):
                    extraction_details["found_pf100_patterns"].append(
                        {
                            "pattern": "simple_pf100phi_mention_count",
                            "count": pf100_mentions,
                        }
                    )

        if pf_counts["PF150φ"] == 0:
            pf150_mentions = len(re.findall(r"PF150[φΦ]", analysis_text, re.IGNORECASE))
            if pf150_mentions > 0:
                extraction_details = pf_counts.get("extraction_details")
                if isinstance(extraction_details, dict):
                    extraction_details["found_pf150_patterns"].append(
                        {
                            "pattern": "simple_pf150phi_mention_count",
                            "count": pf150_mentions,
                        }
                    )

    except Exception as e:
        print(f"⚠️ PF100φ/PF150φカウント抽出エラー: {e}")
        pf_counts["extraction_error"] = str(e)

    return pf_counts


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
