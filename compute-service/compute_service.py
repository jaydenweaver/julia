import os
import json
import hashlib
from collections import namedtuple
from functools import lru_cache
from io import BytesIO
from datetime import datetime

import numpy as np
from PIL import Image
import matplotlib.cm as cm
import httpx
import boto3

os.loadenv()

AWS_REGION = os.getenv("AWS_REGION")

with open("sets.json", "r") as f:
    julia_constants = json.load(f)

julia_res = namedtuple(
    "julia_res", ["image", "real", "imaginary", "iters", "width", "height"]
)

ssm = boto3.client("ssm", region_name=AWS_REGION)
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
    except httpx.HTTPError as e:
        print(f"Time API request failed: {e}")
    return None


def hash_tuple(vals):
    seed = f"{vals[0]}_{vals[1]}"
    hash_bytes = hashlib.sha256(seed.encode("utf-8")).digest()
    hash_a = int.from_bytes(hash_bytes, "big")

    seed = f"{vals[0]}_{vals[1]}_second"
    hash_bytes = hashlib.sha256(seed.encode("utf-8")).digest()
    hash_b = int.from_bytes(hash_bytes, "big")
    return hash_a, hash_b


async def map_to_julia_constants(country, city):
    val = await get_time(country, city)
    if val is None:
        return 0.355, 0.355
    hash_vals = hash_tuple(val)
    i = (hash_vals[0] & hash_vals[1]) % len(julia_constants)
    return julia_constants[i]["a"], julia_constants[i]["b"]


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
    return size_map.get(size.lower())


async def create_julia_image(country="", city="", size="m", center=(0.0, 0.0), zoom=1.0, max_iter=1000):
    a, b = await map_to_julia_constants(country, city)

    w, h = get_size_dimensions(size) or (2000, 1125)
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
