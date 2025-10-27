from fastapi import FastAPI, Query
from datetime import datetime
import json
import boto3
import os
from dotenv import load_dotenv
import httpx

load_dotenv()

DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL")
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-2")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")

sqs = boto3.client("sqs", region_name=AWS_REGION)
app = FastAPI()


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
    user: dict = None
):
    """
    Queues a Julia image generation task in SQS.
    Returns immediately. If cached, returns presigned URL instead.
    """
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
        "message": f"julia compute task queued for {file_name}"
    }
