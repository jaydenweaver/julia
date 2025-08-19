import jwt
from datetime import datetime, timezone, timedelta
import os
from dotenv import load_dotenv
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

load_dotenv()
secret_key = os.getenv("SECRET_KEY")


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


def create_access_token(username):
    payload = {
        'username': username,
        'exp': datetime.now(timezone.utc) +
        timedelta(minutes=30)
    }
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    return token


def authenticate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials or not credentials.scheme == 'Bearer':
        raise HTTPException(status_code=401, detail='Unauthorized')
    token = credentials.credentials
    try:
        user = jwt.decode(token, secret_key, algorithms=['HS256'])
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail='Token expired')
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail='Invalid token')


async def optional_auth(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))):
    if credentials:
        return authenticate_token(credentials)
    return None


async def login(request: Request):
    data = await request.json()
    username = data.get('username')
    password = data.get('password')
    user = users.get(username)
    if not user or user['password'] != password:
        raise HTTPException(status_code=401, detail='Unauthorized')
    token = create_access_token(username)
    return {'authToken': token}
