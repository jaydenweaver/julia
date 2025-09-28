import os
import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import boto3
from botocore.exceptions import ClientError
import hmac
import hashlib
import base64
import json
from jose import jwt

router = APIRouter()

AWS_REGION = os.getenv("AWS_REGION")
USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

cognito_client = boto3.client("cognito-idp", region_name=AWS_REGION)
ssm = boto3.client("ssm", region_name=AWS_REGION)

security = HTTPBearer()

jwks_url_response = ssm.get_parameter(
    Name="/n10807144-a2/jwks-url",
    WithDecryption=True
)

JWKS_URL = jwks_url_response["Parameter"]["Value"]
JWKS = requests.get(JWKS_URL).json()

def get_public_key(token: str):
    headers = jwt.get_unverified_header(token)
    kid = headers["kid"]

    key = next((k for k in JWKS["keys"] if k["kid"] == kid), None)
    if not key:
        raise HTTPException(status_code=401, detail="Public key not found in JWKS")
    return key



def get_secret_hash(username: str) -> str:
    message = username + CLIENT_ID
    dig = hmac.new(
        CLIENT_SECRET.encode("utf-8"),
        msg=message.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    return base64.b64encode(dig).decode()

def authenticate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials or credentials.scheme != "Bearer":
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = credentials.credentials
    try:
        key = get_public_key(token)
        claims = jwt.decode(
            token,
            key,
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


async def signup(request: Request):
    data = await request.json()
    try:
        res = cognito_client.sign_up(
            ClientId=CLIENT_ID,
            SecretHash=get_secret_hash(data["username"]),
            Username=data["username"],
            Password=data["password"],
            UserAttributes=[
                {"Name": "email", "Value": data["email"]}
            ],
        )
        return {"msg": "Sign-up successful, please confirm", "res": res}
    except ClientError as e:
        raise HTTPException(status_code=400, detail=str(e))


async def confirm(request: Request):
    data = await request.json()
    try:
        res = cognito_client.confirm_sign_up(
            ClientId=CLIENT_ID,
            SecretHash=get_secret_hash(data["username"]),
            Username=data["username"],
            ConfirmationCode=data["code"],
        )
        return {"msg": "User confirmed", "res": res}
    except ClientError as e:
        raise HTTPException(status_code=400, detail=str(e))


async def login(request: Request):
    data = await request.json()
    username = data.get("username")
    password = data.get("password")
    mfa_code = data.get("mfa_code")
    session = data.get("session")

    try:
        if mfa_code and session:
            response = cognito_client.respond_to_auth_challenge(
                ClientId=CLIENT_ID,
                ChallengeName="EMAIL_OTP",
                Session=session,
                ChallengeResponses={
                    "USERNAME": username,
                    "EMAIL_OTP_CODE": mfa_code,
                    "SECRET_HASH": get_secret_hash(username)
                }
            )
        else:
            if not password:
                raise HTTPException(status_code=400, detail="Password is required for first step")

            response = cognito_client.initiate_auth(
                AuthFlow="USER_PASSWORD_AUTH",
                AuthParameters={
                    "USERNAME": username,
                    "PASSWORD": password,
                    "SECRET_HASH":get_secret_hash(username),
                },
                ClientId=CLIENT_ID
            )

        if "ChallengeName" in response:
            return {
                "mfa_required": True,
                "challenge_name": response["ChallengeName"],
                "session": response.get("Session")
            }

        if "AuthenticationResult" in response:
            return {
                "mfa_required": False,
                "id_token": response["AuthenticationResult"]["IdToken"],
                "access_token": response["AuthenticationResult"]["AccessToken"],
                "refresh_token": response["AuthenticationResult"]["RefreshToken"]
            }

        raise HTTPException(status_code=500, detail="Unexpected Cognito response")

    except ClientError as e:
        raise HTTPException(status_code=400, detail=e.response["Error"]["Message"])