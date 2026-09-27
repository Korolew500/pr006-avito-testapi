from __future__ import annotations

import os
import uuid

import pytest

from api_client import assert_status


def test_successful_responses_have_json_content_type(client, user_factory):
    user = user_factory()
    response = client.authorize(user["username"], user["password"])
    assert_status(response, 200)
    assert "application/json" in response.headers.get("Content-Type", "").lower()


@pytest.mark.performance
def test_authorization_response_time(client, user_factory):
    user = user_factory()
    limit_ms = float(os.getenv("MAX_RESPONSE_TIME_MS", "5000"))

    response = client.authorize(user["username"], user["password"])

    assert_status(response, 200)
    elapsed_ms = response.elapsed.total_seconds() * 1000
    assert elapsed_ms <= limit_ms, (
        f"Авторизация заняла {elapsed_ms:.1f} мс при лимите {limit_ms:.1f} мс"
    )


def test_unsupported_method_is_not_processed_as_success(client):
    response = client.request("GET", "/api/1/register")
    assert response.status_code in {401, 404, 405}, (
        "Неподдерживаемый метод не должен обрабатываться как успешный: "
        f"получен HTTP {response.status_code}"
    )


@pytest.mark.security
def test_sql_like_username_does_not_bypass_authentication(client):
    username = f"' OR 1=1 --_{uuid.uuid4().hex}"
    password = f"Qa!2026_{uuid.uuid4().hex}"
    registration = client.register(username, password)
    assert registration.status_code in {201, 400}, (
        "Строка должна быть безопасно обработана как данные либо отклонена валидацией; "
        f"получен HTTP {registration.status_code}"
    )
    wrong_auth = client.authorize(username, "definitely-wrong-password")
    assert wrong_auth.status_code in {400, 401}, (
        "SQL-подобная строка не должна приводить к обходу авторизации"
    )
