from fastapi import Query
from fastapi.responses import FileResponse
from datetime import datetime
from julia_set import create_julia_image, julia_res
from data import cache_check_filename, s3_get_presigned_url
import os
import requests
import json

# move this to an external cache at some point (elasticache)
julia_cache = {}


def save_metadata(file: str, entry: dict):
    with open(file, "r+") as f:
        data = json.load(f)
        data["fractals"].append(entry)

        f.seek(0)
        json.dump(data, f, indent=4)
        f.truncate()


async def get_julia_image_time(
        country: str = Query(...),
        city: str = Query(...),
        size: str = Query(...),
        user=None,
        save_dir="images",
        metadata_file="metadata.json"
):

    # check if user has access level for given size
    # just hard coded for now...
    # size xl is admin only
    if size == 'verybig':
        if not user or user['username'] != 'admin':
            return {'invalid permissions'}

    # only users can request large
    if size == 'xxl' and not user:
        return {'invalid permissions'}

    # get cache key
    time_key = datetime.utcnow().strftime("%Y-%m-%d-%H-%M")
    key = f"{country.lower()}_{city.lower()}_{size.lower()}_{time_key}"

    # check if we already have the request in cache
    if cache_check_filename(key):
        # return fetch from presigned url here
        return requests.get(s3_get_presigned_url(key))

    req = await create_julia_image(country=country, city=city, size=size)
    if req is None:
        return {'image creation failed'}

    file_name = f"{key}.png"
    file_path = os.path.join(save_dir, file_name)
    req.image.save(file_path)
    julia_cache[key] = file_path  # store in cache

    metadata = {
        "region": country,
        "city": city,
        "size": size,
        "resolution": {"width": req.width,
                       "height": req.height},
        "params": {"real": req.real,
                   "imaginary": req.imaginary,
                   "iterations": req.iters},
        "file_name": file_name,
        "generated_at": datetime.now().isoformat()
    }
    save_metadata(metadata_file, metadata) # replace with db_put(item)

    return FileResponse(file_path, media_type="image/png")
