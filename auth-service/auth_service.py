import os
import json
import hmac
import hashlib
import base64
import requests
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import boto3
from botocore.exceptions import ClientError
from jose import jwt

AWS_REGION = os.getenv("AWS_REGION")
CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")

cognito_client = boto3.client("cognito-idp", region_name=AWS_REGION)
secrets_client = boto3.client("secretsmanager", region_name=AWS_REGION)
ssm_client = boto3.client("ssm", region_name=AWS_REGION)

jwks_url_response = ssm_client.get_parameter(
    Name="/n10807144-a2/jwks-url",
    WithDecryption=True
)
JWKS_URL = jwks_url_response["Parameter"]["Value"]
JWKS = requests.get(JWKS_URL).json()

security = HTTPBearer()

def get_public_key(token: str):
    headers = jwt.get_unverified_header(token)
    kid = headers["kid"]
    key = next((k for k in JWKS["keys"] if k["kid"] == kid), None)
    if not key:
        raise HTTPException(status_code=401, detail="Public key not found in JWKS")
    return key


def get_secret_hash(username: str) -> str:
    message = username + CLIENT_ID
    secret_res = secrets_client.get_secret_value(SecretId="JULIA_CLIENT_SECRET")
    secret_string = secret_res["SecretString"]
    client_secret = json.loads(secret_string)["COGNITO_CLIENT_SECRET"]
    dig = hmac.new(
        client_secret.encode("utf-8"),
        msg=message.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(dig).decode()


def authenticate_token(credentials: HTTPAuthorizationCredentials):
    if not credentials or credentials.scheme != "Bearer":
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = credentials.credentials
    try:
        key = get_public_key(token)
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=CLIENT_ID
        )
        return claims
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


def cognito_signup(username: str, password: str, email: str):
    return cognito_client.sign_up(
        ClientId=CLIENT_ID,
        SecretHash=get_secret_hash(username),
        Username=username,
        Password=password,
        UserAttributes=[{"Name": "email", "Value": email}],
    )


def cognito_confirm(username: str, code: str):
    return cognito_client.confirm_sign_up(
        ClientId=CLIENT_ID,
        SecretHash=get_secret_hash(username),
        Username=username,
        ConfirmationCode=code,
    )


def cognito_login(username: str, password: str = None, mfa_code: str = None, session: str = None):
    if mfa_code and session:
        return cognito_client.respond_to_auth_challenge(
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
        return cognito_client.initiate_auth(
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password,
                "SECRET_HASH": get_secret_hash(username),
            },
            ClientId=CLIENT_ID
        )
