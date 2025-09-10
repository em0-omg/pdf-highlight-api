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
    図面PDFファイルを画像に変換し、Gemini AIでPF100/PF150の検出・カウントを実行する
    
    Parameters:
    - file: PDF図面ファイル（アップロード）
    - dpi: 画像変換解像度（デフォルト200）
    - prompt: AI分析プロンプト（図面解析・PF100/PF150カウント用にカスタマイズ済み）
    
    Returns:
    - 図面分析結果
    - PF100/PF150のカウント数
    - 画像プレビュー
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
        print("🎨 画像プレビューデータを作成中...")
        preview_images = _create_image_previews(images)
        print("✅ プレビューデータ作成完了")
        
        # Gemini分析を実行
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

        # PF100/PF150のカウント結果を抽出
        pf_counts = _extract_pf_counts(overall_analysis)
        
        print(f"🎉 PDF分析完了: {file.filename}")
        
        return {
            "filename": file.filename,
            "total_pages": len(images),
            "analysis": overall_analysis,
            "pf_counts": pf_counts,
            "images": preview_images,
            "prompt": prompt,
            "dpi": dpi,
            "analysis_type": "図面PDF解析 (PF100/PF150カウント)"
        }
        
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
