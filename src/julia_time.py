from fastapi import Query
from fastapi.responses import FileResponse, StreamingResponse
from datetime import datetime
from src.julia_set import create_julia_image
from src.data import *
from io import BytesIO
import requests
import json

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
        user=None
):

    groups = user.get("cognito:groups", []) if user else []

    # check if user has access level for given size
    # just hard coded for now...
    # size m is admin only
    if size == 'm':
        if "Admins" not in groups:
            return {'invalid permissions'}

    # only users can request small
    if size == 's' and not user:
        return {'invalid permissions'}

    # get cache key
    time_key = datetime.utcnow().strftime("%Y-%m-%d-%H-%M")
    key = f"{country.lower()}_{city.lower()}_{size.lower()}_{time_key}"

    # check if we already have the request in cache, return if true
    if cache_check_filename(key):
        print(f"filename, {key}, found in cache! fetching file from s3...")
        res = requests.get(s3_get_presigned_url(key))
        if res.status_code != 200:
            return {'failed to fetch image!'}
        
        return StreamingResponse(
            res.iter_content(chunk_size=8192),
            media_type=res.headers.get("Content-Type", "application/octet-stream")
        )

    # request not in storage, generate file...
    print(f"filename, {key}, not found in cache! generating image...")
    req = await create_julia_image(country=country, city=city, size=size)
    if req is None:
        return {'image creation failed'}

    # create image buffer
    buf = BytesIO()
    req.image.save(buf, format="PNG") 
    buf.seek(0)       

    file_name = f"{key}.png"
    cache_filename(file_name) # store in memcached

    # write image to s3
    s3_write_image(key=key, image_bytes=buf.getvalue())

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
    db_put(metadata)                 

    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
