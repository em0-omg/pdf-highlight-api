from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import fitz  # type: ignore
import io
import random
from typing import List
from dataclasses import dataclass
from urllib.parse import quote

app = FastAPI(title="PDF Highlight API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@dataclass
class Coordinate:
    x: float
    y: float
    page: int


def simulate_ai_analysis(pdf_doc: fitz.Document) -> List[Coordinate]:
    """
    AI解析をシミュレートしてランダムな座標を返す関数
    実際のAI解析では、PDF内容を分析してハイライトすべき箇所を特定する
    """
    coordinates = []

    for page_num in range(len(pdf_doc)):
        page = pdf_doc[page_num]
        rect = page.rect

        # ページあたり1-5個のランダムなハイライト
        highlights_per_page = random.randint(1, 5)

        for _ in range(highlights_per_page):
            # ページの端から少し内側にランダムな座標を生成
            margin = 50
            x = random.uniform(margin, rect.width - margin)
            y = random.uniform(margin, rect.height - margin)

            coordinates.append(Coordinate(x=x, y=y, page=page_num))

    return coordinates


@app.get("/")
async def hello_world():
    return {"message": "PDF Highlight API is running"}


@app.post("/highlight-pdf")
async def highlight_pdf_with_ai_analysis(file: UploadFile = File(...)):
    """
    AI解析をシミュレートして、PDFの複数箇所にハイライトを追加する
    """
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        pdf_bytes = await file.read()
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        # AI解析をシミュレートして座標を取得
        coordinates = simulate_ai_analysis(pdf_doc)

        # ページ数を事前に取得
        pages_count = len(pdf_doc)

        # 各座標にハイライトを追加
        for coord in coordinates:
            page = pdf_doc[coord.page]
            radius = 15

            # ハイライト用の矩形を作成
            highlight_rect = fitz.Rect(
                coord.x - radius, coord.y - radius, coord.x + radius, coord.y + radius
            )

            # ハイライトを追加（fill色は指定しない）
            highlight = page.add_highlight_annot(highlight_rect)
            highlight.set_colors({"stroke": [1, 0.8, 0]})  # オレンジ色（stroke のみ）
            highlight.update()

        output_buffer = io.BytesIO()
        pdf_doc.save(output_buffer)
        pdf_doc.close()

        output_buffer.seek(0)
        pdf_bytes = output_buffer.getvalue()

        # レスポンスヘッダーに解析結果の情報を含める
        total_highlights = len(coordinates)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{quote(f'ai_highlighted_{file.filename}')}",
                "X-Total-Highlights": str(total_highlights),
                "X-Pages-Processed": str(pages_count),
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
