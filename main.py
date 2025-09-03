from fastapi import FastAPI
import uvicorn

app = FastAPI(title="PDF Highlight API", version="0.1.0")


@app.get("/")
async def hello_world():
    return {"message": "Hello World"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
