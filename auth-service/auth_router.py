from fastapi import FastAPI, Request, HTTPException
from . import auth_service

app = FastAPI()

@app.post("/signup")
async def signup(request: Request):
    data = await request.json()
    try:
        res = auth_service.cognito_signup(
            username=data["username"],
            password=data["password"],
            email=data["email"]
        )
        return {"msg": "Sign-up successful, please confirm", "res": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/confirm")
async def confirm(request: Request):
    data = await request.json()
    try:
        res = auth_service.cognito_confirm(
            username=data["username"],
            code=data["code"]
        )
        return {"msg": "User confirmed", "res": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/login")
async def login(request: Request):
    data = await request.json()
    try:
        response = auth_service.cognito_login(
            username=data.get("username"),
            password=data.get("password"),
            mfa_code=data.get("mfa_code"),
            session=data.get("session")
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
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
