from fastapi import FastAPI, Request, Query, Depends
from contextlib import asynccontextmanager
import json
import os
import shutil
from dotenv import load_dotenv
from src import auth
from src import julia_time

load_dotenv()

SAVE_DIR = "images"
METADATA_FILE = "metadata.json"


def setup_directory():
    # reset stored images...
    if os.path.exists(SAVE_DIR):
        shutil.rmtree(SAVE_DIR)
    os.makedirs(SAVE_DIR, exist_ok=True)

    # reset metadata
    if os.path.exists(METADATA_FILE):
        os.remove(METADATA_FILE)

    with open(METADATA_FILE, "w") as f:
        json.dump({"fractals": []}, f, indent=4)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_directory()
    yield

app = FastAPI(lifespan=lifespan)


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
async def login(request: Request):
    return await auth.login(request)
