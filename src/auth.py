import os
import requests
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
import boto3
from botocore.exceptions import ClientError

router = APIRouter()

AWS_REGION = os.getenv("AWS_REGION")
USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")

cognito_client = boto3.client("cognito-idp", region_name=AWS_REGION)

security = HTTPBearer()

JWKS_URL = f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"
JWKS = requests.get(JWKS_URL).json()


def authenticate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials or credentials.scheme != "Bearer":
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = credentials.credentials
    try:
        claims = jwt.decode(
            token,
            JWKS,
            algorithms=["RS256"],
            audience=CLIENT_ID,
        )
        return claims
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


async def optional_auth(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))):
    if credentials:
        return authenticate_token(credentials)
    return None


async def signup(username: str, password: str, email: str):
    try:
        res = cognito_client.sign_up(
            ClientId=CLIENT_ID,
            Username=username,
            Password=password,
            UserAttributes=[{"Name": "email", "Value": email}],
        )
        return {"msg": "Sign-up successful, please confirm", "res": res}
    except ClientError as e:
        raise HTTPException(status_code=400, detail=str(e))


async def confirm(username: str, code: str):
    try:
        res = cognito_client.confirm_sign_up(
            ClientId=CLIENT_ID,
            Username=username,
            ConfirmationCode=code,
        )
        return {"msg": "User confirmed", "res": res}
    except ClientError as e:
        raise HTTPException(status_code=400, detail=str(e))


async def login(username: str, password: str):
    try:
        res = cognito_client.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password},
        )
        return {
            "AccessToken": res["AuthenticationResult"]["AccessToken"],
            "IdToken": res["AuthenticationResult"]["IdToken"],
            "RefreshToken": res["AuthenticationResult"]["RefreshToken"],
            "ExpiresIn": res["AuthenticationResult"]["ExpiresIn"],
        }
    except ClientError as e:
        raise HTTPException(status_code=401, detail="Login failed: " + str(e))