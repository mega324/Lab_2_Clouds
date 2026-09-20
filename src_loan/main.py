# -*- coding: utf-8 -*-
import os
from model_utils import load_model, make_inference
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi_utils import Oauth2ClientCredentials
from pydantic import BaseModel, Field
from keycloak.uma_permissions import AuthStatus
from keycloak_utils import get_keycloak_data


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

keycloak_openid, token_endpoint = get_keycloak_data()
oauth2_scheme = Oauth2ClientCredentials(tokenUrl=token_endpoint)

model_path: str = os.getenv("MODEL_PATH")
if model_path is None:
    raise ValueError("The environment variable $MODEL_PATH is empty!")


async def get_token_status(token: str) -> AuthStatus:
    """Проверяет токен и права доступа через UMA-запрос к Keycloak."""
    return keycloak_openid.has_uma_access(token, "infer_endpoint#doInfer")


async def check_token(token: str = Depends(oauth2_scheme)) -> None:
    """Зависимость FastAPI: проверяет токен и права на инференс."""
    auth_status = await get_token_status(token)
    is_logged = auth_status.is_logged_in
    is_authorized = auth_status.is_authorized

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
    return make_inference(load_model(model_path), instance.model_dump())