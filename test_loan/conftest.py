# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Устанавливаем переменные окружения ДО импорта
sys.path.insert(0, str(Path(__file__).parent.parent / "src_loan"))

os.environ["MODEL_PATH"] = str(Path(__file__).parent.parent / "models" / "pipeline.pkl")
os.environ["KEYCLOAK_URL"] = "https://keycloak:8443"
os.environ["CLIENT_ID"] = "inference-client"
os.environ["CLIENT_SECRET"] = "dummy_secret"

# Мокаем keycloak_utils ДО импорта main.py
import keycloak_utils

# Заменяем функцию get_keycloak_data на заглушку
def _fake_get_keycloak_data():
    mock_openid = MagicMock()
    mock_openid.has_uma_access = MagicMock(return_value=MagicMock(
        is_logged_in=True,
        is_authorized=True,
    ))
    return mock_openid, "https://keycloak:8443/realms/inference/protocol/openid-connect/token"

keycloak_utils.get_keycloak_data = _fake_get_keycloak_data