from fastapi import FastAPI
from fastapi.responses import FileResponse
import uuid
import os
import shutil
from juliaset import create_julia_image
from datetime import datetime

save_dir = "images"

# delete old images...
shutil.rmtree(save_dir)
os.makedirs(save_dir, exist_ok=True)

julia_cache = {}

users = {
    'user': {
        'username': 'user',
        'password': 'pass'
    },
    'admin': {
        'username': 'admin',
        'password': 'pass'
    }
}


app = FastAPI()


@app.get("/time/{country}/{city}")
async def get_julia_image_time(country: str, city: str):
    # get cache key
    time_key = datetime.utcnow().strftime("%Y-%m-%d-%H-%M")
    key = (country.lower(), city.lower(), time_key)

    # check if we already have the request in cache
    if key in julia_cache:
        file_path = julia_cache[key]
        if os.path.exists(file_path):
            return FileResponse(file_path, media_type="image/png")
        else:
            del julia_cache[key]

    img = await create_julia_image(country=country, city=city)
    if img is None:
        return {'image creation failed'}

    file_name = f"{key}.png"
    file_path = os.path.join(save_dir, file_name)
    img.save(file_path)
    julia_cache[key] = file_path  # store in cache

    return FileResponse(file_path, media_type="image/png")
