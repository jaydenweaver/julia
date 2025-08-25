from fastapi import FastAPI, Request, Query, Depends
import os
import shutil
from src import auth
from src import julia_time


SAVE_DIR = "images"
METADATA_FILE = "metadata.json"

# delete old images...
shutil.rmtree(SAVE_DIR)
os.makedirs(SAVE_DIR, exist_ok=True)


app = FastAPI()


@app.get("/time")
async def get_julia_image_time(
        country: str = Query(...),
        city: str = Query(...),
        size: str = Query(...),
        user=Depends(auth.optional_auth)
):
    return await julia_time.get_julia_image_time(country, city,
                                                 size, user, SAVE_DIR)


@app.post("/login")
async def login(Request: Request):
    return await auth.login(Request)
