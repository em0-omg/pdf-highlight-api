from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pdf2image import convert_from_bytes
import uvicorn
import io
import base64
import os
from PIL import Image
from src.infrastructure.gemini import GeminiImageAnalyzer

app = FastAPI(title="PDF Analysis API", version="0.1.0")

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
        "message": "PDF Analysis API is running",
        "gemini_available": gemini_available,
        "status": "✅ Ready" if gemini_available else "⚠️ Gemini API Key required",
        "setup_help": "Set GEMINI_API_KEY in .env file" if not gemini_available else None
    }


@app.post("/analyze-pdf")
async def analyze_pdf(
    file: UploadFile = File(...), 
    dpi: int = 200,
    prompt: str = Query("この文書について説明してください。", description="Analysis prompt")
):
    """
    PDFファイルを画像に変換し、Gemini AIで分析する
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
        
        print(f"🎉 PDF分析完了: {file.filename}")
        
        return {
            "filename": file.filename,
            "total_pages": len(images),
            "analysis": overall_analysis,
            "images": preview_images,
            "prompt": prompt,
            "dpi": dpi
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
