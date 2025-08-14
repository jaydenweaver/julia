import numpy as np
from PIL import Image
import httpx
import hashlib
import matplotlib.cm as cm


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


# maps hash_tuple (256bit ints) to a range between -1.5, 1.5
def hash_to_julia_constant(vals):
    range = 0.4
    norm_a = vals[0] / (2**256 - 1)
    norm_b = vals[1] / (2**256 - 1)
    return -range + norm_a * (range - (-range)), \
        -range + norm_b * (range - (-range))


async def generate_julia_constants(country, city):
    val = await get_time(country, city)
    if val is None:
        val = (0, 0)
    return hash_to_julia_constant(hash_tuple(val))


async def generate_julia_image(country, city,
                               size=(1500, 1000),
                               center=(0.0, 0.0),
                               zoom=1.0,
                               max_iter=500):
    a, b = await generate_julia_constants(country, city)
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
