from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pdf2image import convert_from_bytes
import uvicorn
import io
import zipfile
from urllib.parse import quote

app = FastAPI(title="PDF Highlight API", version="0.1.0")

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/")
async def hello_world():
    return {"message": "PDF Highlight API is running"}


@app.post("/pdf-to-images")
async def pdf_to_images(file: UploadFile = File(...), dpi: int = 200):
    """
    PDFファイルを画像に変換する
    :param file: PDFファイル
    :param dpi: 解像度（デフォルト: 200）
    :return: 画像のZIPファイルまたは単一画像
    """
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        pdf_bytes = await file.read()
        images = convert_from_bytes(pdf_bytes, dpi=dpi)
        
        if len(images) > 1:
            return _create_zip_response(images, file.filename)
        else:
            return _create_single_image_response(images[0], file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error converting PDF: {str(e)}")


def _create_zip_response(images: list, filename: str) -> StreamingResponse:
    """
    複数画像をZIPファイルとして返す
    """
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for i, image in enumerate(images):
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            zip_file.writestr(f'page_{i+1}.png', img_buffer.getvalue())
    
    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename.rsplit('.', 1)[0] + '_images.zip')}"
        }
    )


def _create_single_image_response(image, filename: str) -> StreamingResponse:
    """
    単一画像を返す
    """
    img_buffer = io.BytesIO()
    image.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    return StreamingResponse(
        img_buffer,
        media_type="image/png",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename.rsplit('.', 1)[0] + '.png')}"
        }
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
