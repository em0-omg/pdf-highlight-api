from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pdf2image import convert_from_bytes
from PIL import Image, ImageDraw
import uvicorn
import io
import base64
import os
import time
import logging
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

# Logger setup (stdout)
logger = logging.getLogger("pdf_highlight_api")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Gemini API Key の状態を確認
gemini_api_key = os.getenv("GEMINI_API_KEY")
gemini_analyzer = None
gemini_available = False

if gemini_api_key:
    try:
        gemini_analyzer = GeminiImageAnalyzer()
        gemini_available = True
        print("✅ Gemini API Key found. Analysis features are available.")
        logger.info("Gemini initialized and available")
    except Exception as e:
        print(f"❌ Error initializing Gemini: {e}")
        print("🔧 Please check your GEMINI_API_KEY.")
        logger.exception("Failed to initialize Gemini")
else:
    print("⚠️  GEMINI_API_KEY not found.")
    print("🔧 Please set GEMINI_API_KEY in your .env file to enable analysis features.")
    print("📝 Get your API key from: https://makersuite.google.com/app/apikey")
    logger.warning("GEMINI_API_KEY not found; analysis endpoints unavailable")

@app.get("/")
async def hello_world():
    return {
        "message": "図面PDF解析API is running",
        "description": "図面PDFを分析し、PF100/PF150の文言とポイント数をカウントする特化型API",
        "gemini_available": gemini_available,
        "grok_available": grok_available,
        "status": "✅ Ready" if (gemini_available or grok_available) else "⚠️ API Key required",
        "setup_help": {
            "gemini": "Set GEMINI_API_KEY in .env file" if not gemini_available else "Available",
            "grok": "Set XAI_API_KEY in .env file" if not grok_available else "Available"
        },
        "features": [
            "PF100/PF150文言検出",
            "記号位置座標検出",
            "自動カウント",
            "ハイライト表示",
            "Gemini & Grok AI 分析",
        ],
    }


@app.post("/gemini/document-analyze")
async def gemini_document_analyze(
    file: UploadFile = File(..., description="PDFファイルをアップロード"),
    prompt: str = Query(
        "このPDFは図面を表しています。100mm径パイプシャフト(PF100)か、防火ダンパー付き (FD付) の150mm径パイプシャフト (PF150) を各所探して、各ページ上の座標を教えてください。もし可能なら座標をx,y形式で教えてください。",
        description="Geminiに渡す追加指示文（ベースプロンプトに追記されます）",
    ),
    model: str = Query(
        "gemini-2.5-pro",
        description="使用するGeminiモデル（例: gemini-2.5-pro, gemini-2.5-flash）",
    ),
    debug: bool = Query(False, description="デバッグ情報（プロンプト/生出力など）を含める"),
    dpi: int = Query(200, description="プレビュー画像のDPI（解像度）"),
):
    """
    PDFをGeminiに渡して解析結果を返す。

    - 入力: PDFファイル + 任意のプロンプト
    - 出力: Geminiの解析結果（JSON形式）
    """
    if not gemini_available:
        raise HTTPException(
            status_code=503,
            detail="Gemini analysis service is not available. Please set GEMINI_API_KEY.",
        )

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        pdf_bytes = await file.read()
        
        # PDFを画像に変換してプレビュー用のデータを作成
        print(f"🖼️  PDFを画像に変換中... (DPI: {dpi})")
        images = convert_from_bytes(pdf_bytes, dpi=dpi)
        print(f"✅ 変換完了: {len(images)}ページの画像を生成")
        
        # 画像プレビューデータを作成
        preview_images = _create_image_previews(images)
        
        # Geminiで解析
        analyzer = GeminiImageAnalyzer(model_name=model)
        result_json = await analyzer.analyze_pdf_document(pdf_bytes, prompt, debug=debug)
        
        # ハイライト付き画像を作成
        highlighted_images = []
        if isinstance(result_json, dict) and "pages" in result_json:
            highlighted_images = _create_highlighted_images(images, result_json)

        response_payload = {
            "filename": file.filename,
            "model": model,
            "prompt": prompt,
            "result": result_json,
            "preview_images": preview_images,
            "highlighted_images": highlighted_images,
            "total_pages": len(images),
        }

        return response_payload
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Gemini document analyze error")
        raise HTTPException(status_code=500, detail=f"Error analyzing PDF with Gemini: {str(e)}")


@app.post("/analyze-pdf")
async def analyze_pdf(
    file: UploadFile = File(...),
    dpi: int = 300,
    highlight: bool = Query(True, description="ハイライト機能を有効にするかどうか"),
    target_image: UploadFile = File(
        None, description="検出対象の記号画像（オプション）"
    ),
    model: str = Query(
        "gemini-2.5-pro",
        description="使用するGeminiモデル（gemini-2.5-pro または gemini-2.5-flash）",
    ),
    debug: bool = Query(False, description="デバッグ情報（検出根拠・プロンプト等）を付加する"),
):
    """
    PDFファイル内の記号を検出してハイライト表示する

    Parameters:
    - file: PDFファイル（アップロード）
    - dpi: 画像変換解像度（デフォルト200）
    - highlight: ハイライト機能有効化フラグ（デフォルトTrue）
    - target_image: 検出対象の記号画像（オプション、指定しない場合はデフォルトのtarget.pngを使用）
    - model: 使用するGeminiモデル

    Returns:
    - 検出された記号の座標情報
    - ハイライト付き画像（highlight=Trueの場合）
    """
    print(f"📄 ハイライト処理開始: {file.filename}")
    logger.info(
        "Analyze request: file=%s dpi=%s highlight=%s model=%s custom_target=%s",
        file.filename,
        dpi,
        highlight,
        model,
        bool(target_image),
    )

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
        t0 = time.perf_counter()
        images = convert_from_bytes(pdf_bytes, dpi=dpi)
        t1 = time.perf_counter()
        print(f"✅ 変換完了: {len(images)}ページの画像を生成")
        logger.info("PDF converted: pages=%d time_ms=%.1f", len(images), (t1 - t0) * 1000)

        # 画像プレビューデータを作成
        print("🎨 元画像プレビューデータを作成中...")
        preview_images = _create_image_previews(images)
        print("✅ 元画像プレビューデータ作成完了")

        # カスタムターゲット画像の処理
        custom_target_image = None
        if target_image:
            target_bytes = await target_image.read()
            img_buffer = io.BytesIO(target_bytes)
            custom_target_image = Image.open(img_buffer)
            print(f"🎯 カスタムターゲット画像を使用: {target_image.filename}")

        # 検出・説明に使用するモデルの初期化
        highlighted_images = []
        all_detection_data = []
        target_overview = None

        print(f"🤖 使用モデル: {model}")
        try:
            model_analyzer = GeminiImageAnalyzer(model_name=model)
        except Exception as e:
            print(f"❌ モデル初期化エラー: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize model {model}: {str(e)}",
            )

        # ターゲット画像の特徴説明（読み込み確認用）
        try:
            target_overview = await model_analyzer.describe_target_image(
                custom_target_image
            )
            print("🔎 ターゲット画像の特徴説明を取得")
        except Exception as e:
            print(f"⚠️ ターゲット画像説明エラー: {str(e)}")
            target_overview = {
                "error": f"ターゲット画像の説明に失敗: {str(e)}"
            }

        total_detections = 0
        if highlight:
            print("🎯 記号検出を開始")

            for i, image in enumerate(images):
                print(f"📍 ページ{i+1}: 記号検出中...")
                if model_analyzer:
                    page_start = time.perf_counter()
                    detection_data = (
                        await model_analyzer.analyze_symbol_with_coordinates(
                            image,
                            custom_target_image,
                            debug=debug,
                            target_description=(
                                target_overview.get("description") if isinstance(target_overview, dict) else None
                            ),
                        )
                    )
                    page_end = time.perf_counter()
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
                        page_cnt = detection_data.get("summary", {}).get(
                            "total_detections", len(detection_data.get("detections", []))
                        )
                        total_detections += int(page_cnt or 0)
                        logger.info(
                            "Page %d analyzed: detections=%s time_ms=%.1f",
                            i + 1,
                            page_cnt,
                            (page_end - page_start) * 1000,
                        )
                    else:
                        print(
                            f"⚠️ ページ{i+1}: 座標検出エラー - {detection_data.get('error', '不明なエラー')}"
                        )
                        logger.warning(
                            "Page %d detection error: %s",
                            i + 1,
                            detection_data.get("error", "unknown"),
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
                    logger.error("Page %d skipped: Gemini not available", i + 1)
                    highlighted_images.append(
                        {"page": i + 1, "error": "Gemini分析機能を利用できません"}
                    )
            print("✅ 全ページのハイライト処理完了")
            logger.info(
                "Highlighting finished: pages=%d total_detections=%d",
                len(images),
                total_detections,
            )

        print(f"🎉 ハイライト処理完了: {file.filename}")
        logger.info(
            "Analyze completed: file=%s pages=%d dpi=%d highlight=%s model=%s detections=%d",
            file.filename,
            len(images),
            dpi,
            highlight,
            model,
            total_detections,
        )

        response_data = {
            "filename": file.filename,
            "total_pages": len(images),
            "images": preview_images,
            "dpi": dpi,
            "highlight_enabled": highlight,
            "analysis_type": "記号検出API",
            "custom_target_used": target_image is not None,
        }

        # ハイライトデータの追加
        response_data["highlighted_images"] = highlighted_images
        response_data["detection_data"] = all_detection_data
        response_data["target_image_overview"] = target_overview

        return response_data

    except Exception as e:
        print(f"❌ PDF処理エラー: {str(e)}")
        logger.exception("Unhandled error while processing PDF")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@app.post("/gemini/pipe-shaft-detect")
async def gemini_pipe_shaft_detect(
    file: UploadFile = File(..., description="PDFファイルをアップロード"),
    model: str = Query(
        "gemini-2.5-pro",
        description="使用するGeminiモデル（例: gemini-2.5-pro, gemini-2.5-flash）",
    ),
    debug: bool = Query(False, description="デバッグ情報（プロンプト/生出力など）を含める"),
    dpi: int = Query(200, description="画像変換時のDPI（解像度）"),
):
    """
    PDFからパイプシャフトの座標を検出する。
    
    - 入力: PDFファイル
    - 処理: PDFを画像に変換し、Geminiで解析
    - 出力: パイプシャフトの座標情報（JSON形式）
    """
    if not gemini_available:
        raise HTTPException(
            status_code=503,
            detail="Gemini analysis service is not available. Please set GEMINI_API_KEY.",
        )

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        pdf_bytes = await file.read()
        
        # PDFを画像に変換
        print(f"🖼️  PDFを画像に変換中... (DPI: {dpi})")
        images = convert_from_bytes(pdf_bytes, dpi=dpi)
        print(f"✅ 変換完了: {len(images)}ページの画像を生成")
        
        # 画像プレビューデータを作成
        preview_images = _create_image_previews(images)
        
        # Geminiで解析（パイプシャフト検出用のプロンプトを使用）
        analyzer = GeminiImageAnalyzer(model_name=model)
        result_json = await analyzer.analyze_pipe_shafts(pdf_bytes, debug=debug)
        
        # ハイライト付き画像を作成
        highlighted_images = []
        if isinstance(result_json, dict) and "pages" in result_json:
            highlighted_images = _create_highlighted_images(images, result_json)

        response_payload = {
            "filename": file.filename,
            "model": model,
            "result": result_json,
            "preview_images": preview_images,
            "highlighted_images": highlighted_images,
            "total_pages": len(images),
        }

        return response_payload
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Gemini pipe shaft detection error")
        raise HTTPException(status_code=500, detail=f"Error analyzing PDF with Gemini: {str(e)}")

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


def _create_highlighted_images(images: list, detection_data: dict) -> list:
    """
    検出結果に基づいてハイライト付き画像を作成
    座標は1-1000の範囲でスケーリングされているため、実際の画像サイズに変換
    PF100とPF150のみをハイライト表示
    """
    highlighted_images = []
    
    # 検出データがpages形式の場合の処理
    if "pages" in detection_data:
        pages_data = {page["page"]: page["detections"] for page in detection_data.get("pages", [])}
    else:
        # 他の形式の場合は空の辞書
        pages_data = {}
    
    for i, image in enumerate(images):
        page_num = i + 1
        # 画像をコピーして描画用に準備
        img_copy = image.copy()
        draw = ImageDraw.Draw(img_copy)
        
        # 画像の実際のサイズを取得
        img_width, img_height = img_copy.size
        
        # この ページの検出データを取得
        page_detections = pages_data.get(page_num, [])
        
        # 各検出位置にハイライトを描画（PF100とPF150のみ）
        for detection in page_detections:
            # targetまたはtypeフィールドをチェック
            target_type = detection.get("target", "") or detection.get("type", "")
            
            # PF100またはPF150のみハイライト
            if "PF100" not in target_type and "PF150" not in target_type:
                continue
                
            if "position" in detection and "x" in detection["position"] and "y" in detection["position"]:
                # 1-1000の座標を実際の画像座標に変換（中心座標）
                x = int(detection["position"]["x"] * img_width / 1000)
                y = int(detection["position"]["y"] * img_height / 1000)
                
                # ターゲットタイプによって色を変える
                if "PF100" in target_type:
                    color = "red"
                    outline_color = "darkred"
                elif "PF150" in target_type:
                    color = "blue"
                    outline_color = "darkblue"
                
                # ハイライト円を描画（半径は画像サイズに応じて調整）
                radius = max(30, min(img_width, img_height) // 35)
                draw.ellipse(
                    [(x - radius, y - radius), (x + radius, y + radius)],
                    outline=outline_color,
                    width=4
                )
                # 中心点を描画
                draw.ellipse(
                    [(x - 6, y - 6), (x + 6, y + 6)],
                    fill=color
                )
        
        # Base64エンコード
        img_buffer = io.BytesIO()
        img_copy.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
        
        highlighted_images.append({
            "page": page_num,
            "image_data": f"data:image/png;base64,{img_base64}",
            "detections": page_detections
        })
    
    return highlighted_images


@app.post("/detect-target-image")
async def detect_target_image(
    file: UploadFile = File(..., description="PDFファイルをアップロード"),
    target_image: UploadFile = File(None, description="検出対象の画像（省略時はtarget.png使用）"),
    model: str = Query(
        "gemini-2.5-pro",
        description="使用するGeminiモデル（例: gemini-2.5-pro, gemini-2.5-flash）",
    ),
    debug: bool = Query(False, description="デバッグ情報（プロンプト/生出力など）を含める"),
    dpi: int = Query(200, description="画像変換時のDPI（解像度）"),
):
    """
    PDFから指定画像（デフォルト: target.png）と同じパターンを検出する。
    
    - 入力: PDFファイルとターゲット画像（オプション）
    - 処理: PDFを画像に変換し、Geminiで画像マッチング
    - 出力: 検出位置の座標情報（JSON形式）とハイライト画像
    """
    if not gemini_available:
        raise HTTPException(
            status_code=503,
            detail="Gemini analysis service is not available. Please set GEMINI_API_KEY.",
        )

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        pdf_bytes = await file.read()
        
        # PDFを画像に変換
        print(f"🖼️  PDFを画像に変換中... (DPI: {dpi})")
        images = convert_from_bytes(pdf_bytes, dpi=dpi)
        print(f"✅ 変換完了: {len(images)}ページの画像を生成")
        
        # 画像プレビューデータを作成
        preview_images = _create_image_previews(images)
        
        # カスタムターゲット画像の処理
        custom_target_image = None
        if target_image:
            target_bytes = await target_image.read()
            img_buffer = io.BytesIO(target_bytes)
            custom_target_image = Image.open(img_buffer)
            print(f"🎯 カスタムターゲット画像を使用: {target_image.filename}")
        
        # Geminiで解析（画像マッチング）
        analyzer = GeminiImageAnalyzer(model_name=model)
        result_json = await analyzer.detect_target_image_in_pdf(
            pdf_bytes, 
            custom_target_image=custom_target_image,
            debug=debug
        )
        
        # ハイライト付き画像を作成
        highlighted_images = []
        if isinstance(result_json, dict) and "pages" in result_json:
            highlighted_images = _create_target_highlighted_images(images, result_json)

        response_payload = {
            "filename": file.filename,
            "model": model,
            "result": result_json,
            "preview_images": preview_images,
            "highlighted_images": highlighted_images,
            "total_pages": len(images),
            "target_image": "custom" if target_image else "default (target.png)",
        }

        return response_payload
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Target image detection error")
        raise HTTPException(status_code=500, detail=f"Error analyzing PDF with Gemini: {str(e)}")


def _create_target_highlighted_images(images: list, detection_data: dict) -> list:
    """
    ターゲット画像検出結果に基づいてハイライト付き画像を作成
    position.x,y座標を中心に矩形を描画
    """
    highlighted_images = []
    
    # 検出データがpages形式の場合の処理
    if "pages" in detection_data:
        pages_data = {page["page"]: page["detections"] for page in detection_data.get("pages", [])}
    else:
        pages_data = {}
    
    for i, image in enumerate(images):
        page_num = i + 1
        # 画像をコピーして描画用に準備
        img_copy = image.copy()
        draw = ImageDraw.Draw(img_copy)
        
        # 画像の実際のサイズを取得
        img_width, img_height = img_copy.size
        
        # このページの検出データを取得
        page_detections = pages_data.get(page_num, [])
        
        # 各検出位置にハイライトを描画
        for detection in page_detections:
            if "position" in detection and "x" in detection["position"] and "y" in detection["position"]:
                # 1-1000の座標を実際の画像座標に変換（中心座標）
                x = int(detection["position"]["x"] * img_width / 1000)
                y = int(detection["position"]["y"] * img_height / 1000)
                
                # 赤い矩形でハイライト（target.pngのサイズに基づいて調整）
                half_width = max(20, min(img_width, img_height) // 50)
                half_height = max(20, min(img_width, img_height) // 50)
                
                # 矩形を描画
                draw.rectangle(
                    [(x - half_width, y - half_height), (x + half_width, y + half_height)],
                    outline="red",
                    width=3
                )
                
                # 中心に十字マークを描画
                cross_size = 10
                draw.line([(x - cross_size, y), (x + cross_size, y)], fill="red", width=2)
                draw.line([(x, y - cross_size), (x, y + cross_size)], fill="red", width=2)
        
        # Base64エンコード
        img_buffer = io.BytesIO()
        img_copy.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
        
        highlighted_images.append({
            "page": page_num,
            "image_data": f"data:image/png;base64,{img_base64}",
            "detections": page_detections
        })
    
    return highlighted_images


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
