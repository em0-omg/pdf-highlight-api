from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import fitz
import io

app = FastAPI(title="PDF Highlight API", version="0.1.0")

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


@app.post("/highlight-pdf")
async def highlight_pdf_center(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        pdf_bytes = await file.read()
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            rect = page.rect
            
            center_x = rect.width / 2
            center_y = rect.height / 2
            radius = 20
            
            circle = fitz.Rect(center_x - radius, center_y - radius, 
                             center_x + radius, center_y + radius)
            
            highlight = page.add_highlight_annot(circle)
            highlight.set_colors({"stroke": [1, 1, 0], "fill": [1, 1, 0]})
            highlight.update()
        
        output_buffer = io.BytesIO()
        pdf_doc.save(output_buffer)
        pdf_doc.close()
        
        output_buffer.seek(0)
        pdf_bytes = output_buffer.getvalue()
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=highlighted_{file.filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
