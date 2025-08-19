from fastapi import FastAPI, Request, Query, Depends
from fastapi.responses import FileResponse
import os
import shutil
from juliaset import create_julia_image
from datetime import datetime
import auth


save_dir = "images"

# delete old images...
shutil.rmtree(save_dir)
os.makedirs(save_dir, exist_ok=True)

julia_cache = {}


app = FastAPI()


@app.get("/time")
async def get_julia_image_time(
        country: str = Query(...),
        city: str = Query(...),
        size: str = Query(...),
        user=Depends(auth.optional_auth)
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


@app.post("/login")
async def login(Request: Request):
    return await auth.login(Request)
