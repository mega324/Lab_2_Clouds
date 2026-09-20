# -*- coding: utf-8 -*-
import os
import requests
import urllib3
from model_utils import load_model, make_inference
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi_utils import Oauth2ClientCredentials
from pydantic import BaseModel, Field

urllib3.disable_warnings()


class LoanInstance(BaseModel):
    """Схема входных данных для предсказания одобрения кредита."""
    no_of_dependents: int = Field(..., ge=0, description="Количество иждивенцев")
    education: str = Field(..., description="Образование: 'Graduate' или 'Not Graduate'")
    self_employed: str = Field(..., description="Самозанятый: 'Yes' или 'No'")
    income_annum: int = Field(..., ge=0, description="Годовой доход")
    loan_amount: int = Field(..., ge=0, description="Сумма кредита")
    loan_term: int = Field(..., gt=0, description="Срок кредита (месяцы)")
    cibil_score: int = Field(..., ge=300, le=900, description="Кредитный рейтинг CIBIL")
    residential_assets_value: int = Field(..., description="Стоимость жилых активов")
    commercial_assets_value: int = Field(..., ge=0, description="Стоимость коммерческих активов")
    luxury_assets_value: int = Field(..., ge=0, description="Стоимость люксовых активов")
    bank_asset_value: int = Field(..., ge=0, description="Банковские активы")


app = FastAPI(
    title="Loan Approval Prediction Service",
    description="Сервис инференса с аутентификацией через Keycloak",
    version="2.0.0",
)

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
MODEL_PATH = os.getenv("MODEL_PATH")

if not KEYCLOAK_URL:
    raise ValueError("The environment variable $KEYCLOAK_URL is empty!")
if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError("The client's credentials aren't defined!")
if not MODEL_PATH:
    raise ValueError("The environment variable $MODEL_PATH is empty!")

TOKEN_ENDPOINT = f"{KEYCLOAK_URL}/realms/inference/protocol/openid-connect/token"
oauth2_scheme = Oauth2ClientCredentials(tokenUrl=TOKEN_ENDPOINT)


async def get_token_status(token: str) -> dict:
    """Проверяет токен и права доступа через introspect + UMA-запрос."""
    # 1. Introspect — валиден ли токен
    introspect_url = f"{KEYCLOAK_URL}/realms/inference/protocol/openid-connect/token/introspect"
    r_introspect = requests.post(
        introspect_url,
        data={
            "token": token,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        verify=False,
        timeout=10,
    )
    introspect_data = r_introspect.json()
    is_logged = introspect_data.get("active", False)

    if not is_logged:
        return {"is_logged": False, "is_authorized": False}

    # 2. UMA-запрос — есть ли права на ресурс
    r_uma = requests.post(
        TOKEN_ENDPOINT,
        headers={"Authorization": f"Bearer {token}"},
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:uma-ticket",
            "audience": CLIENT_ID,
            "permission": "infer_endpoint#doInfer",
            "response_mode": "decision",
        },
        verify=False,
        timeout=10,
    )
    uma_data = r_uma.json()
    is_authorized = uma_data.get("result", False)

    return {"is_logged": is_logged, "is_authorized": is_authorized}


async def check_token(token: str = Depends(oauth2_scheme)) -> None:
    """Зависимость FastAPI: проверяет токен и права на инференс."""
    print("--- check_token called ---")
    print("token:", token[:50] + "..." if token else "None")

    token_status = await get_token_status(token)
    print("status:", token_status)

    is_logged = token_status.get("is_logged", False)
    is_authorized = token_status.get("is_authorized", False)

    print("is_logged:", is_logged)
    print("is_authorized:", is_authorized)
    print("--- end check_token ---")

    if not is_logged:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not is_authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.get("/healthcheck")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/predictions")
async def predictions(instance: LoanInstance,
                      token: str = Depends(check_token)) -> dict:
    return make_inference(load_model(MODEL_PATH), instance.model_dump())