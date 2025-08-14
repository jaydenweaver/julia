from fastapi import FastAPI  # , File, UploadFile
from fastapi.staticfiles import StaticFiles
# import uuid
import os
# import httpx
from juliaset import generate_julia_image
from PIL import Image

os.makedirs("images", exist_ok=True)


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


@app.get("/time")
async def get_julia_image():
    img = generate_julia_image('Australia', 'Brisbane')
    if img is None:
        return {'works': 'None'}
    return {'works': 'yes'}


app.mount("/", StaticFiles(directory="../client/dist", html=True),
          name="static")
