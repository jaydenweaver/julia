from fastapi import FastAPI, Request, Query, Depends, HTTPException
from fastapi.responses import Response
from dotenv import load_dotenv
import httpx
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from datetime import datetime
import json
import boto3

load_dotenv()

app = FastAPI()

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL")
DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-2")

sqs = boto3.client("sqs", region_name=AWS_REGION)
security = HTTPBearer(auto_error=False)

@app.get("/get/{file_name}")
async def get_image(file_name: str):
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(f"{DATA_SERVICE_URL}/s3/url/{file_name}")
            res.raise_for_status()
            url = res.json().get("url")
            if not url:
                raise HTTPException(status_code=404, detail=f"No URL found for file: {file_name}")

            image_res = await client.get(url)
            image_res.raise_for_status()

            return Response(content=image_res.content, media_type="image/png")

        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

async def optional_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        return None

    token = credentials.credentials
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(
                f"{AUTH_SERVICE_URL}/verify-token",
                json={"token": token}
            )
            res.raise_for_status()
            return res.json()
        except httpx.HTTPStatusError as e:
            return None
        except Exception as e:
            return None
        
async def get_presigned_url(key: str):
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{DATA_SERVICE_URL}/s3/url/{key}")
        res.raise_for_status()
        return res.json().get("url")


async def check_cache(filename: str):
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{DATA_SERVICE_URL}/cache/{filename}")
        res.raise_for_status()
        return res.json().get("exists", False)


@app.get("/generate")
async def generate_julia(
    country: str = Query(...),
    city: str = Query(...),
    size: str = Query(...),
    user=Depends(optional_auth)
):
    groups = user.get("cognito:groups", []) if user else []

    # permissions
    if size == "m" and "admin" not in groups:
        return {"error": "invalid permissions"}
    if size == "s" and not user:
        return {"error": "invalid permissions"}

    time_key = datetime.utcnow().strftime("%Y-%m-%d-%H-%M")
    file_name = f"{country.lower()}_{city.lower()}_{size.lower()}_{time_key}.png"

    # check cache first
    if await check_cache(file_name):
        url = await get_presigned_url(file_name)
        return {"status": "cached", "url": url}

    # queue compute task
    task = {
        "action": "create_julia_image",
        "country": country,
        "city": city,
        "size": size,
        "file_name": file_name,
        "requested_at": datetime.utcnow().isoformat()
    }

    sqs.send_message(
        QueueUrl=SQS_QUEUE_URL,
        MessageBody=json.dumps(task)
    )

    return {
        "status": "queued",
        "file_name": file_name,
        "message": f"julia compute task queued for {file_name}. retrieve image at: /get/{file_name}"
    }


@app.post("/login")
async def login(request: Request):
    data = await request.json()
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(f"{AUTH_SERVICE_URL}/login", json=data)
            res.raise_for_status()
            return res.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code,
                                detail=e.response.text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/signup")
async def signup(request: Request):
    data = await request.json()
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(f"{AUTH_SERVICE_URL}/signup", json=data)
            res.raise_for_status()
            return res.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code,
                                detail=e.response.text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/confirm")
async def confirm(request: Request):
    data = await request.json()
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(f"{AUTH_SERVICE_URL}/confirm", json=data)
            res.raise_for_status()
            return res.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code,
                                detail=e.response.text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        
        
