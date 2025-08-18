import numpy as np
from PIL import Image
import httpx
import hashlib
import matplotlib.cm as cm
import json

with open("sets.json", "r") as f:
    julia_constants = json.load(f)


# available time zones available at
# https://timeapi.io/documentation/iana-timezones
async def get_time(country, city):
    url = f"https://timeapi.io/api/time/current/zone?timeZone={
        country}%2F{city}"
    print(url)
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            res = await c.get(url)
            res.raise_for_status()
            data = res.json()
            print(data)
            return data['date'], data['time']
    except httpx.HTTPError as e:
        print(f"api request failed: {e}")
    return None


def hash_tuple(vals):
    seed = f"{vals[0]}_{vals[1]}"
    hash_bytes = hashlib.sha256(seed.encode('utf-8')).digest()
    hash_a = int.from_bytes(hash_bytes, "big")

    seed = f"{vals[0]}_{vals[1]}_second"
    hash_bytes = hashlib.sha256(seed.encode('utf-8')).digest()
    hash_b = int.from_bytes(hash_bytes, "big")
    print(f"hash tuple: {hash_a}, {hash_b}")
    return (hash_a, hash_b)


async def map_to_julia_constants(country, city):
    val = await get_time(country, city)
    if val is None:
        return (-0.7, 0.27015)
    hash_vals = hash_tuple(val)
    i = (hash_vals[0] & hash_vals[1] % len(julia_constants))
    a, b = julia_constants[i]["a"], julia_constants[i]["b"]
    return a, b


async def create_julia_image(country="", city="",
                             size=(2500, 1250),
                             center=(0.0, 0.0),
                             zoom=1.0,
                             max_iter=1000):
    a, b = (-0.7, -0.26)
    if country != "":
        a, b = await map_to_julia_constants(country, city)
    print(f"a: {a}, b: {b}")

    w, h = size
    half_x = 1.5 / zoom
    half_y = (h / w) * half_x

    x = np.linspace(center[0] - half_x, center[0] +
                    half_x, w, dtype=np.float64)
    y = np.linspace(center[1] - half_y, center[1] +
                    half_y, h, dtype=np.float64)
    X, Y = np.meshgrid(x, y)
    Z0 = X + 1j * Y
    C = complex(a, b)

    Z = Z0.copy()
    iters = np.zeros(Z.shape, dtype=np.uint16)
    alive = np.ones(Z.shape, dtype=bool)

    for i in range(max_iter):
        Z[alive] = Z[alive] * Z[alive] + C
        escaped = np.greater(np.abs(Z), 2.0, where=alive)
        iters[escaped & alive] = i
        alive &= ~escaped
        if not alive.any():
            break

    norm_iters = iters / max_iter
    colored_img = cm.inferno(norm_iters)[:, :, :3]  # RGB from colormap
    colored_img = (colored_img * 255).astype(np.uint8)

    return Image.fromarray(colored_img)
