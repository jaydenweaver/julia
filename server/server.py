from fastapi import FastAPI  # , File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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


@app.get("/time/{country}/{city}")
async def get_julia_image(country: str, city: str):
    img = await generate_julia_image(country, city)
    if img is None:
        return {'works': 'None'}
    file_path = "julia.png"
    img.save(file_path)
    return FileResponse(file_path, media_type="image/png")

app.mount("/", StaticFiles(directory="../client/dist", html=True),
          name="static")
