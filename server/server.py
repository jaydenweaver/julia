from fastapi import FastAPI, File, UploadFile
import uuid
import os
os.makedirs("uploads", exist_ok=True)

app = FastAPI()


@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    if not file.content_type.startswith("video/"):
        return {"error": "invalid file type"}

    # prepend unique id to avoid filename collisions
    file_path = f"uploads/{uuid.uuid4()}_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
    return {"filename": file.filename, "message": "upload successful"}
