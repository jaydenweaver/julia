from fastapi import FastAPI, Request, Query, Depends
import os
import shutil
from src import auth
from src import julia_time


save_dir = "images"

# delete old images...
shutil.rmtree(save_dir)
os.makedirs(save_dir, exist_ok=True)


app = FastAPI()


@app.get("/time")
async def get_julia_image_time(
        country: str = Query(...),
        city: str = Query(...),
        size: str = Query(...),
        user=Depends(auth.optional_auth)
):
    return await julia_time.get_julia_image_time(country, city,
                                                 size, user, save_dir)


@app.post("/login")
async def login(Request: Request):
    return await auth.login(Request)
