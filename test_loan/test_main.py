# -*- coding: utf-8 -*-
import pytest
from fastapi.testclient import TestClient
import main
from main import app

client = TestClient(app)

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
    "bank_asset_value": 8000000,
}

CORRECT_TOKEN = "test-token"


@pytest.fixture(autouse=True)
def mock_check_token():
    """Мокаем check_token — тесты не обращаются к Keycloak."""
    async def fake_check_token():
        return None

    app.dependency_overrides[main.check_token] = fake_check_token
    yield
    app.dependency_overrides = {}


def test_healthcheck():
    response = client.get("/healthcheck")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_prediction_with_correct_token():
    response = client.post(
        "/predictions",
        json=VALID_INSTANCE,
        headers={"Authorization": f"Bearer {CORRECT_TOKEN}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "loan_status" in data
    assert data["loan_status"] in ("Approved", "Rejected")
    assert 0.0 <= data["probability_approved"] <= 1.0
    assert 0.0 <= data["probability_rejected"] <= 1.0
    assert abs(data["probability_approved"] + data["probability_rejected"] - 1.0) < 0.001


def test_prediction_with_invalid_data():
    invalid = VALID_INSTANCE.copy()
    invalid["cibil_score"] = 10000
    response = client.post(
        "/predictions",
        json=invalid,
        headers={"Authorization": f"Bearer {CORRECT_TOKEN}"},
    )
    assert response.status_code == 422


def test_prediction_missing_field():
    invalid = VALID_INSTANCE.copy()
    del invalid["income_annum"]
    response = client.post(
        "/predictions",
        json=invalid,
        headers={"Authorization": f"Bearer {CORRECT_TOKEN}"},
    )
    assert response.status_code == 422