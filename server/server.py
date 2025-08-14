from fastapi import FastAPI, File, UploadFile
from fastapi.staticfiles import StaticFiles
import uuid
import os
import numpy as np
import hashlib
import requests

os.makedirs("images", exist_ok=True)


def get_time(country, city):
    url = f"https://timeapi.io/api/time/current/zone?timeZone={
        country}%2F{city}"
    print(url)
    try:
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        data = res.json()
        print(data)
        return data['date'], data['time']
    except requests.RequestException as e:
        print(f"api request failed: {e}")
    return None


def hash_tuple(vals):
    seed = f"{vals[0]}_{vals[1]}"
    hash_bytes = hashlib.sha256(seed.encode('utf-8')).digest()
    hash_a = int.from_bytes(hash_bytes, "big")

    seed = f"{vals[0]}_{vals[1]}_second"
    hash_bytes = hashlib.sha256(seed.encode('utf-8')).digest()
    hash_b = int.from_bytes(hash_bytes, "big")

    return (hash_a, hash_b)


# maps hash_tuple (256bit ints) to a range between -1.5, 1.5
def hash_to_julia_constant(val):
    norm_a = val[0] / (2**256 - 1)
    norm_b = val[1] / (2**256 - 1)
    return -1.5 + norm_a * (1.5 - (-1.5)), -1.5 + norm_b * (1.5 - (-1.5))


def generate_julia_constants(country, city):
    val = get_time(country, city)
    if val is None:
        val = (0, 0)
    return hash_to_julia_constant(hash_tuple(val))


app = FastAPI()
app.mount("/static", StaticFiles(directory="../client/dist", html=True),
          name="static")


@app.get("/time")
async def time_json():
    val = generate_julia_constants('Australia', 'Brisbane')
    return {'constant_one': val[0], 'constant_two': val[1]}
