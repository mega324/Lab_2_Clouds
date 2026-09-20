# -*- coding: utf-8 -*-
"""
Тесты для модуля model_utils: загрузка модели и выполнение инференса.

Используется подход с изоляцией внешних зависимостей через monkeypatch
(для функции make_inference) и tmpdir (для тестирования load_model).
"""
import pytest
import pandas as pd
from model_utils import make_inference, load_model
from sklearn.pipeline import Pipeline
from pickle import dumps


@pytest.fixture
def create_data() -> dict[str, int | float | str]:
    """Тестовые входные данные: один объект — кредитная заявка."""
    return {
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


def test_make_inference(monkeypatch, create_data):
    """Проверяем корректность работы make_inference с mock-моделью."""
    def mock_predict(_, data: pd.DataFrame) -> list:
        # Убеждаемся, что DataFrame содержит ровно те же данные
        assert create_data == {
            key: value[0] for key, value in data.to_dict("list").items()
        }
        return [1]  # модель предсказывает класс "Approved"

    def mock_predict_proba(_, data: pd.DataFrame) -> list:
        # Возвращаем вероятности для [Rejected, Approved]
        return [[0.05, 0.95]]

    in_model = Pipeline([])
    monkeypatch.setattr(Pipeline, "predict", mock_predict)
    monkeypatch.setattr(Pipeline, "predict_proba", mock_predict_proba)

    result = make_inference(in_model, create_data)

    assert result == {
        "loan_status": "Approved",
        "probability_approved": 0.95,
        "probability_rejected": 0.05,
    }


@pytest.fixture()
def filepath_and_data(tmpdir):
    """Готовим временный файл с тестовым pickle-объектом."""
    p = tmpdir.mkdir("datadir").join("fakemodel.pkl")
    example: str = "Test message!"
    p.write_binary(dumps(example))
    return str(p), example


def test_load_model(filepath_and_data):
    """Проверяем, что load_model корректно читает pickle-файл."""
    assert filepath_and_data[1] == load_model(filepath_and_data[0])