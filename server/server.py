from fastapi import FastAPI, Request, Query, Depends
import json
import os
import shutil
from src import auth
from src import julia_time

SAVE_DIR = "images"
METADATA_FILE = "metadata.json"


app = FastAPI()


@app.on_event("startup")
def setup_directory():
    # reset stored images...
    shutil.rmtree(SAVE_DIR)
    os.makedirs(SAVE_DIR, exist_ok=True)

    # reset metadata
    if os.path.exists(METADATA_FILE):
        os.remove(METADATA_FILE)

    with open(METADATA_FILE, "w") as f:
        json.dump({"fractals": []}, f, indent=4)


@app.get("/time")
async def get_julia_image_time(
        country: str = Query(...),
        city: str = Query(...),
        size: str = Query(...),
        user=Depends(auth.optional_auth)
):
    return await julia_time.get_julia_image_time(country, city,
                                                 size, user,
                                                 SAVE_DIR, METADATA_FILE)


@app.post("/login")
async def login(Request: Request):
    return await auth.login(Request)
