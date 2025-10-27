from fastapi import FastAPI
from pydantic import BaseModel
import base64
from data_service import DataService

app = FastAPI()
service = DataService()

class MetadataModel(BaseModel):
    file_name: str
    region: str
    city: str
    size: int
    generated_at: str

class ImageUploadModel(BaseModel):
    key: str
    image_base64: str

@app.post("/s3/upload")
def upload_image(req: ImageUploadModel):
    image_bytes = base64.b64decode(req.image_base64)
    service.write_image(req.key, image_bytes)
    return {"message": "Image uploaded", "key": req.key}


@app.delete("/s3/{key}")
def delete_image(key: str):
    service.delete_image(key)
    return {"message": f"Deleted {key}"}


@app.get("/s3/url/{key}")
def get_presigned_url(key: str):
    url = service.get_presigned_url(key)
    return {"url": url}


@app.post("/db/put")
def put_metadata(metadata: MetadataModel):
    service.put_metadata(metadata.dict())
    return {"message": "Metadata added", "file_name": metadata.file_name}


@app.get("/db/{filename}")
def get_metadata(filename: str):
    return service.get_metadata(filename)


@app.post("/cache/{filename}")
def cache_file(filename: str):
    success = service.cache_filename(filename)
    return {"cached": success}


@app.get("/cache/{filename}")
def check_cache(filename: str):
    exists = service.check_cache(filename)
    return {"exists": exists}
