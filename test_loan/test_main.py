# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path

# Добавляем src_loan в путь импорта
sys.path.insert(0, str(Path(__file__).parent.parent / "src_loan"))

# Устанавливаем переменную окружения для модели ПЕРЕД импортом main
os.environ["MODEL_PATH"] = str(Path(__file__).parent.parent / "models" / "pipeline.pkl")

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# Правильные тестовые данные (Approved)
VALID_INSTANCE = {
    "no_of_dependents": 2,
    "education": "Graduate",
    "self_employed": "No",
    "income_annum": 9600000,
    "loan_amount": 29900000,
    "loan_term": 12,
    "cibil_score": 778,
    "residential_assets_value": 2400000,
    "commercial_assets_value": 1760000,
    "luxury_assets_value": 22700000,
    "bank_asset_value": 8000000
}

CORRECT_TOKEN = "00000"
WRONG_TOKEN = "00002"


def test_healthcheck():
    """Проверяем, что /healthcheck работает без авторизации."""
    response = client.get("/healthcheck")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_prediction_with_correct_token():
    """Проверяем валидный инференс с правильным токеном."""
    response = client.post(
        "/predictions",
        json=VALID_INSTANCE,
        headers={"Authorization": f"Bearer {CORRECT_TOKEN}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "loan_status" in data
    assert data["loan_status"] in ("Approved", "Rejected")
    assert 0.0 <= data["probability_approved"] <= 1.0
    assert 0.0 <= data["probability_rejected"] <= 1.0
    # Сумма вероятностей должна быть ~1
    assert abs(data["probability_approved"] + data["probability_rejected"] - 1.0) < 0.001


def test_prediction_without_token():
    """Проверяем, что без токена — 401."""
    response = client.post("/predictions", json=VALID_INSTANCE)
    assert response.status_code == 401


def test_prediction_with_wrong_token():
    """Проверяем, что с неверным токеном — 401."""
    response = client.post(
        "/predictions",
        json=VALID_INSTANCE,
        headers={"Authorization": f"Bearer {WRONG_TOKEN}"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication credentials"


def test_prediction_with_invalid_data():
    """Проверяем, что невалидные данные возвращают 422."""
    invalid = VALID_INSTANCE.copy()
    invalid["cibil_score"] = 10000  # вне диапазона 300-900
    response = client.post(
        "/predictions",
        json=invalid,
        headers={"Authorization": f"Bearer {CORRECT_TOKEN}"}
    )
    assert response.status_code == 422


def test_prediction_missing_field():
    """Проверяем, что пропущенное поле возвращает 422."""
    invalid = VALID_INSTANCE.copy()
    del invalid["income_annum"]
    response = client.post(
        "/predictions",
        json=invalid,
        headers={"Authorization": f"Bearer {CORRECT_TOKEN}"}
    )
    assert response.status_code == 422