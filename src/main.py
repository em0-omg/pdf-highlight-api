from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pdf2image import convert_from_bytes
import uvicorn
import io
import base64
import os
import re
from PIL import Image
from src.infrastructure.gemini import GeminiImageAnalyzer

app = FastAPI(
    title="図面PDF解析API", 
    version="0.2.0",
    description="図面PDFを分析し、PF100/PF150の文言とポイント数をカウントする特化型API"
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
        "setup_help": "Set GEMINI_API_KEY in .env file" if not gemini_available else None,
        "features": [
            "図面PDF分析",
            "PF100/PF150文言検出",
            "ポイント数自動カウント",
            "高解像度画像変換",
            "AI分析レポート"
        ]
    }


@app.post("/analyze-pdf")
async def analyze_pdf(
    file: UploadFile = File(...), 
    dpi: int = 200,
    highlight: bool = Query(True, description="ハイライト機能を有効にするかどうか"),
    prompt: str = Query(
        "この図面PDFを詳しく分析してください。特に以下の点に注目してください：\n"
        "1. 図面内に記載されている「PF100」および「PF150」の文言を全て検出し、それぞれの箇所数をカウントしてください。\n"
        "2. それぞれの文言が指し示すポイント（位置や対象）を特定してください。\n"
        "3. 図面の全体的な構造と主要なコンポーネントを説明してください。\n"
        "4. 検出結果は以下の形式で明記してください：\n"
        "   - PF100: X箇所\n"
        "   - PF150: Y箇所", 
        description="図面PDF解析用のプロンプト（PF100/PF150の検出とカウント）"
    )
):
    """
    図面PDFファイルを画像に変換し、Gemini AIでPF100/PF150の検出・カウント・ハイライトを実行する
    
    Parameters:
    - file: PDF図面ファイル（アップロード）
    - dpi: 画像変換解像度（デフォルト200）
    - highlight: ハイライト機能有効化フラグ（デフォルトTrue）
    - prompt: AI分析プロンプト（図面解析・PF100/PF150カウント用にカスタマイズ済み）
    
    Returns:
    - 図面分析結果
    - PF100/PF150のカウント数と座標情報
    - 元画像プレビュー
    - ハイライト付き画像プレビュー（highlight=Trueの場合）
    - メタデータ
    """
    print(f"📄 PDF分析開始: {file.filename}")
    
    if not gemini_available:
        print("❌ Gemini API不可: APIキーが設定されていません")
        raise HTTPException(
            status_code=503, 
            detail="Gemini analysis service is not available. Please set GEMINI_API_KEY in your .env file. Get your API key from: https://makersuite.google.com/app/apikey"
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
            print("🎯 座標検出とハイライト処理を開始...")
            for i, image in enumerate(images):
                print(f"📍 ページ{i+1}: 座標検出中...")
                detection_data = await gemini_analyzer.analyze_image_with_coordinates(image)
                all_detection_data.append(detection_data)
                
                if "error" not in detection_data:
                    print(f"🎨 ページ{i+1}: ハイライト描画中...")
                    highlighted_image = gemini_analyzer.create_highlighted_image(image, detection_data)
                    
                    # ハイライト済み画像をBase64エンコード
                    img_buffer = io.BytesIO()
                    highlighted_image.save(img_buffer, format='PNG')
                    img_buffer.seek(0)
                    img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
                    
                    highlighted_images.append({
                        "page": i + 1,
                        "image_data": f"data:image/png;base64,{img_base64}",
                        "detections": detection_data.get("detections", []),
                        "summary": detection_data.get("summary", {})
                    })
                    print(f"✅ ページ{i+1}: ハイライト完了")
                else:
                    print(f"⚠️ ページ{i+1}: 座標検出エラー - {detection_data.get('error', '不明なエラー')}")
                    highlighted_images.append({
                        "page": i + 1,
                        "error": detection_data.get("error", "座標検出に失敗しました")
                    })
            print("✅ 全ページのハイライト処理完了")
        
        # 従来のGemini分析を実行
        print("🤖 AI分析を開始...")
        if len(images) > 1:
            print(f"📚 複数ページ分析: {len(images)}ページを順次処理中...")
            analysis_results = await gemini_analyzer.analyze_images(images, prompt)
            overall_analysis = f"全{len(images)}ページの分析結果:\n" + "\n\n".join([f"ページ{i+1}: {result}" for i, result in enumerate(analysis_results)])
            print("✅ 複数ページ分析完了")
        else:
            print("📄 単一ページ分析中...")
            overall_analysis = await gemini_analyzer.analyze_image(images[0], prompt)
            print("✅ 単一ページ分析完了")

        # PF100/PF150のカウント結果を抽出（座標データとテキスト分析を統合）
        pf_counts = _extract_pf_counts(overall_analysis)
        
        # 座標データから正確なカウントを取得
        if all_detection_data:
            coordinate_counts = {"PF100": 0, "PF150": 0, "total_detections": 0}
            for detection_data in all_detection_data:
                if "summary" in detection_data:
                    coordinate_counts["PF100"] += detection_data["summary"].get("pf100_count", 0)
                    coordinate_counts["PF150"] += detection_data["summary"].get("pf150_count", 0)
                    coordinate_counts["total_detections"] += detection_data["summary"].get("total_detections", 0)
            
            # 座標ベースのカウントをメインに使用
            pf_counts["coordinate_based"] = coordinate_counts
        
        print(f"🎉 PDF分析完了: {file.filename}")
        
        response_data = {
            "filename": file.filename,
            "total_pages": len(images),
            "analysis": overall_analysis,
            "pf_counts": pf_counts,
            "images": preview_images,
            "prompt": prompt,
            "dpi": dpi,
            "highlight_enabled": highlight,
            "analysis_type": "図面PDF解析 (PF100/PF150カウント・ハイライト)"
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
        image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        preview_images.append({
            "page": i + 1,
            "image_data": f"data:image/png;base64,{img_base64}"
        })
    
    return preview_images


def _extract_pf_counts(analysis_text: str) -> dict:
    """
    AI分析結果からPF100とPF150のカウント数を抽出
    """
    pf_counts = {
        "PF100": 0,
        "PF150": 0,
        "extraction_details": {
            "found_pf100_patterns": [],
            "found_pf150_patterns": []
        }
    }
    
    try:
        # PF100のパターンを検索
        pf100_patterns = [
            r'PF100[:\s]*(\d+)[箇個ヶ]所',
            r'PF100[:\s]*(\d+)箇所',
            r'PF100[:\s]*(\d+)個',
            r'PF100[:\s]*(\d+)ヶ所',
            r'PF100[:\s]*(\d+)\s*箇所',
            r'「?PF100」?[:\s]*(\d+)',
            r'PF100.*?(\d+)箇所',
            r'PF100.*?(\d+)個所'
        ]
        
        # PF150のパターンを検索
        pf150_patterns = [
            r'PF150[:\s]*(\d+)[箇個ヶ]所',
            r'PF150[:\s]*(\d+)箇所',
            r'PF150[:\s]*(\d+)個',
            r'PF150[:\s]*(\d+)ヶ所',
            r'PF150[:\s]*(\d+)\s*箇所',
            r'「?PF150」?[:\s]*(\d+)',
            r'PF150.*?(\d+)箇所',
            r'PF150.*?(\d+)個所'
        ]
        
        # PF100を検索
        for pattern in pf100_patterns:
            matches = re.findall(pattern, analysis_text, re.IGNORECASE)
            if matches:
                pf_counts["PF100"] = int(matches[0])
                pf_counts["extraction_details"]["found_pf100_patterns"].append({
                    "pattern": pattern,
                    "count": int(matches[0])
                })
                break
        
        # PF150を検索
        for pattern in pf150_patterns:
            matches = re.findall(pattern, analysis_text, re.IGNORECASE)
            if matches:
                pf_counts["PF150"] = int(matches[0])
                pf_counts["extraction_details"]["found_pf150_patterns"].append({
                    "pattern": pattern,
                    "count": int(matches[0])
                })
                break
                
        # 単純な文字列検索もバックアップとして実行
        if pf_counts["PF100"] == 0:
            pf100_mentions = len(re.findall(r'PF100', analysis_text, re.IGNORECASE))
            if pf100_mentions > 0:
                pf_counts["extraction_details"]["found_pf100_patterns"].append({
                    "pattern": "simple_mention_count",
                    "count": pf100_mentions
                })
        
        if pf_counts["PF150"] == 0:
            pf150_mentions = len(re.findall(r'PF150', analysis_text, re.IGNORECASE))
            if pf150_mentions > 0:
                pf_counts["extraction_details"]["found_pf150_patterns"].append({
                    "pattern": "simple_mention_count", 
                    "count": pf150_mentions
                })
                
    except Exception as e:
        print(f"⚠️ PFカウント抽出エラー: {e}")
        pf_counts["extraction_error"] = str(e)
    
    return pf_counts


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
