from fastapi import FastAPI, Request, Query, Depends, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import httpx
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

load_dotenv()

app = FastAPI()

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL")
COMPUTE_SERVICE_URL = os.getenv("COMPUTE_SERVICE_URL")

security = HTTPBearer(auto_error=False)

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

@app.get("/time")
async def get_julia_image_time(
    country: str = Query(...),
    city: str = Query(...),
    size: str = Query(...),
    user=Depends(optional_auth)
):
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(
                f"{COMPUTE_SERVICE_URL}/time",
                params={"country": country, "city": city, "size": size},
                headers={"User": str(user) if user else ""}
            )
            res.raise_for_status()
            return res.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code,
                                detail=e.response.text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


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
        
        
