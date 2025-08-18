from fastapi import FastAPI
from fastapi.responses import FileResponse
import uuid
import os
import shutil
from juliaset import create_julia_image

save_dir = "images"

# delete old images...
shutil.rmtree(save_dir)
os.makedirs(save_dir, exist_ok=True)


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
async def get_julia_image_time(country: str, city: str):
    img = await create_julia_image(country=country, city=city)
    if img is None:
        return {'works': 'None'}
    unique_id = str(uuid.uuid4())
    file_name = f"{unique_id}_{country}_{city}.png"
    file_path = os.path.join(save_dir, file_name)
    img.save(file_path)
    return FileResponse(file_path, media_type="image/png")
