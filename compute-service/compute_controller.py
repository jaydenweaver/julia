from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from io import BytesIO
from datetime import datetime
import base64
import httpx
import os

from compute_service import create_julia_image

os.loadenv()
DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL")

app = FastAPI()

async def upload_image(key: str, image_bytes: bytes):
    img_b64 = base64.b64encode(image_bytes).decode("utf-8")
    async with httpx.AsyncClient() as client:
        await client.post(f"{DATA_SERVICE_URL}/s3/upload", json={
            "key": key,
            "image_base64": img_b64
        })


async def get_presigned_url(key: str):
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{DATA_SERVICE_URL}/s3/url/{key}")
        return res.json().get("url")


async def put_metadata(metadata: dict):
    async with httpx.AsyncClient() as client:
        await client.post(f"{DATA_SERVICE_URL}/db/put", json=metadata)


async def cache_file(filename: str):
    async with httpx.AsyncClient() as client:
        await client.post(f"{DATA_SERVICE_URL}/cache/{filename}")


async def check_cache(filename: str):
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{DATA_SERVICE_URL}/cache/{filename}")
        return res.json().get("exists", False)


@app.get("/generate")
async def generate_julia(
    country: str = Query(...),
    city: str = Query(...),
    size: str = Query(...),
    user: dict = None
):
    groups = user.get("cognito:groups", []) if user else []

    if size == "m" and "admin" not in groups:
        return {"error": "invalid permissions"}
    if size == "s" and not user:
        return {"error": "invalid permissions"}

    time_key = datetime.utcnow().strftime("%Y-%m-%d-%H-%M")
    file_name = f"{country.lower()}_{city.lower()}_{size.lower()}_{time_key}.png"

    # check cache
    if await check_cache(file_name):
        url = await get_presigned_url(file_name)
        return StreamingResponse(
            httpx.stream("GET", url),
            media_type="image/png"
        )

    # generate image
    result = await create_julia_image(country, city, size)
    buf = BytesIO()
    result.image.save(buf, format="PNG")
    buf.seek(0)

    # cache, upload to s3, save metadata
    await cache_file(file_name)
    await upload_image(file_name, buf.getvalue())

    metadata = {
        "file_name": file_name,
        "region": country,
        "city": city,
        "size": size,
        "resolution": {"width": result.width, "height": result.height},
        "params": {"real": result.real, "imaginary": result.imaginary, "iterations": result.iters},
        "generated_at": datetime.utcnow().isoformat()
    }
    await put_metadata(metadata)

    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
