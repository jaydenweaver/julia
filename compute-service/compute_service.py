import os
import json
import time
import base64
import hashlib
from collections import namedtuple
from functools import lru_cache
from datetime import datetime
from io import BytesIO
import asyncio

import numpy as np
from PIL import Image
import matplotlib.cm as cm
import httpx
import boto3
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-2")
DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")

sqs = boto3.client("sqs", region_name=AWS_REGION)
ssm = boto3.client("ssm", region_name=AWS_REGION)

with open("sets.json", "r") as f:
    julia_constants = json.load(f)

julia_res = namedtuple(
    "julia_res", ["image", "real", "imaginary", "iters", "width", "height"]
)

external_api_response = ssm.get_parameter(
    Name="/n10807144-a2/external-api",
    WithDecryption=True
)
EXTERNAL_API_URL = external_api_response["Parameter"]["Value"]

async def get_time(country, city):
    url = f"{EXTERNAL_API_URL}{country}%2F{city}"
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            res = await c.get(url)
            res.raise_for_status()
            data = res.json()
            return data["date"], data["time"]
    except Exception as e:
        print(f"failed to get time for {city}, {country}: {e}")
    return None


def hash_tuple(vals):
    seed = f"{vals[0]}_{vals[1]}"
    h1 = int.from_bytes(hashlib.sha256(seed.encode()).digest(), "big")
    h2 = int.from_bytes(hashlib.sha256((seed + '_b').encode()).digest(), "big")
    return h1, h2


async def map_to_julia_constants(country, city):
    val = await get_time(country, city)
    if val is None:
        return 0.355, 0.355
    h1, h2 = hash_tuple(val)
    i = (h1 ^ h2) % len(julia_constants)
    c = julia_constants[i]
    return c["a"], c["b"]


@lru_cache(maxsize=None)
def get_size_dimensions(size: str):
    size_map = {
        "s": (1000, 563),
        "m": (2000, 1125),
        "l": (3000, 1688),
        "xl": (4000, 2250),
        "xxl": (5000, 2813),
        "verybig": (8000, 4500),
    }
    return size_map.get(size.lower(), (2000, 1125))


async def create_julia_image(country, city, size, center=(0.0, 0.0), zoom=1.0, max_iter=1000):
    a, b = await map_to_julia_constants(country, city)
    w, h = get_size_dimensions(size)
    half_x = 1.5 / zoom
    half_y = (h / w) * half_x

    x = np.linspace(center[0] - half_x, center[0] + half_x, w, dtype=np.float32)
    y = np.linspace(center[1] - half_y, center[1] + half_y, h, dtype=np.float32)

    C = np.complex64(complex(a, b))
    img = Image.new("RGB", (w, h))

    for j, y_val in enumerate(y):
        X_row = x.astype(np.complex64)
        Y_row = np.full_like(X_row, y_val, dtype=np.float32)
        Z = X_row + 1j * Y_row
        iters_row = np.zeros(Z.shape, dtype=np.uint16)
        alive = np.ones(Z.shape, dtype=bool)

        for i in range(max_iter):
            Z[alive] = Z[alive] * Z[alive] + C
            escaped = np.abs(Z) > 2.0
            iters_row[escaped & alive] = i
            alive &= ~escaped
            if not alive.any():
                break

        norm_row = iters_row / max_iter
        colored_row = (cm.inferno(norm_row)[:, :3] * 255).astype(np.uint8)
        row_img = Image.fromarray(colored_row[np.newaxis, :, :], mode="RGB")
        img.paste(row_img, (0, j))

    return julia_res(image=img, real=float(a), imaginary=float(b), iters=max_iter, width=w, height=h)

async def upload_image(key: str, image_bytes: bytes):
    img_b64 = base64.b64encode(image_bytes).decode("utf-8")
    async with httpx.AsyncClient() as client:
        await client.post(f"{DATA_SERVICE_URL}/s3/upload", json={
            "key": key,
            "image_base64": img_b64
        })

async def put_metadata(metadata: dict):
    async with httpx.AsyncClient() as client:
        await client.post(f"{DATA_SERVICE_URL}/db/put", json=metadata)


async def cache_file(filename: str):
    async with httpx.AsyncClient() as client:
        await client.post(f"{DATA_SERVICE_URL}/cache/{filename}")

async def process_message(task):
    country = task["country"]
    city = task["city"]
    size = task["size"]
    file_name = task["file_name"]

    print(f"processing julia task for {file_name}")

    result = await create_julia_image(country, city, size)
    buf = BytesIO()
    result.image.save(buf, format="PNG")
    buf.seek(0)

    await upload_image(file_name, buf.getvalue())
    await cache_file(file_name)

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

    print(f"completed Julia image {file_name}")


async def poll_sqs():
    while True:
        messages = sqs.receive_message(
            QueueUrl=SQS_QUEUE_URL,
            MaxNumberOfMessages=5,
            WaitTimeSeconds=10
        ).get("Messages", [])

        if not messages:
            await asyncio.sleep(1)
            continue

        for msg in messages:
            try:
                body = json.loads(msg["Body"])
                await process_message(body)
                sqs.delete_message(
                    QueueUrl=SQS_QUEUE_URL,
                    ReceiptHandle=msg["ReceiptHandle"]
                )
            except Exception as e:
                print(f"Failed to process message: {e}")

if __name__ == "__main__":
    asyncio.run(poll_sqs())
