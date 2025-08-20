from fastapi import Query
from fastapi.responses import FileResponse
from datetime import datetime
from src.juliaset import create_julia_image
import os


julia_cache = {}


async def get_julia_image_time(
        country: str = Query(...),
        city: str = Query(...),
        size: str = Query(...),
        user=None,
        save_dir="images"
):

    # check if user has access level for given size
    # just hard coded for now...
    if size == 'xl':
        if not user or user['username'] != 'admin':
            return {'invalid permissions'}

    # only users can request large
    if size == 'l' and not user:
        return {'invalid permissions'}

    # get cache key
    time_key = datetime.utcnow().strftime("%Y-%m-%d-%H-%M")
    key = (country.lower(), city.lower(), size.lower(), time_key)

    # check if we already have the request in cache
    if key in julia_cache:
        file_path = julia_cache[key]
        if os.path.exists(file_path):
            print(f"returning cached image! {file_path}")
            return FileResponse(file_path, media_type="image/png")
        else:
            del julia_cache[key]

    img = await create_julia_image(country=country, city=city, size=size)
    if img is None:
        return {'image creation failed'}

    file_name = f"{key}.png"
    file_path = os.path.join(save_dir, file_name)
    img.save(file_path)
    julia_cache[key] = file_path  # store in cache

    return FileResponse(file_path, media_type="image/png")
