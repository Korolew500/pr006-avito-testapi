from __future__ import annotations

import uuid

from api_client import assert_status, json_body


def test_register_unique_user_returns_id_and_username(client):
    username = f"register_{uuid.uuid4().hex}"
    password = f"Qa!2026_{uuid.uuid4().hex}"

    response = client.register(username, password)

    assert_status(response, 201)
    body = json_body(response)
    assert isinstance(body, dict)
    assert isinstance(body.get("id"), int) and body["id"] > 0
    assert body.get("username") == username
    assert "password" not in body, "Пароль не должен возвращаться в ответе регистрации"


def test_register_duplicate_username_returns_409(client):
    username = f"duplicate_{uuid.uuid4().hex}"
    password = f"Qa!2026_{uuid.uuid4().hex}"
    assert_status(client.register(username, password), 201)

    duplicate = client.register(username, password)

    assert_status(duplicate, 409)


def test_register_without_username_returns_400(client):
    response = client.request(
        "POST", "/api/1/register", json_body={"password": "Qa!2026_valid_password"}
    )
    assert_status(response, 400)


def test_register_without_password_returns_400(client):
    response = client.request(
        "POST", "/api/1/register", json_body={"username": f"missing_{uuid.uuid4().hex}"}
    )
    assert_status(response, 400)


def test_register_empty_credentials_returns_400(client):
    assert_status(client.register("", ""), 400)


def test_register_malformed_json_returns_400(client):
    response = client.request(
        "POST",
        "/api/1/register",
        headers={"Content-Type": "application/json"},
        data='{"username":',
    )
    assert_status(response, 400)


def test_authorize_registered_user_returns_bearer_token(user_factory):
    user = user_factory()
    assert isinstance(user["token"], str) and user["token"]


def test_authorize_with_wrong_password_returns_401(client, user_factory):
    user = user_factory()
    response = client.authorize(user["username"], f"wrong_{uuid.uuid4().hex}")
    assert_status(response, 401)


def test_authorize_unknown_user_returns_401(client):
    response = client.authorize(f"unknown_{uuid.uuid4().hex}", f"Qa!2026_{uuid.uuid4().hex}")
    assert_status(response, 401)


def test_authorize_without_required_field_returns_400(client):
    response = client.request(
        "POST", "/api/1/autorize", json_body={"username": f"user_{uuid.uuid4().hex}"}
    )
    assert_status(response, 400)


def test_public_endpoints_do_not_require_authorization_header(client):
    username = f"public_{uuid.uuid4().hex}"
    password = f"Qa!2026_{uuid.uuid4().hex}"
    registration = client.register(username, password)
    assert_status(registration, 201)
    authorization = client.authorize(username, password)
    assert_status(authorization, 200)
