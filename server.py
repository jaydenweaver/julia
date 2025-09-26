from fastapi import FastAPI, Request, Query, Depends
from contextlib import asynccontextmanager
import json
import os
import shutil
from dotenv import load_dotenv
from src import auth
from src import julia_time

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
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
                                                 size, user)

@app.post("/login")
async def login(request: Request):
    return await auth.login(request)

@app.post("/signup")
async def signup(request: Request):
    return await auth.signup(request)

@app.post("/confirm")
async def confirm(request: Request):
    return await auth.confirm(request)