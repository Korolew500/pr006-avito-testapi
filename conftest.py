from __future__ import annotations

import os
import uuid
from collections.abc import Callable, Generator
from typing import Any

import pytest

from api_client import ApiClient, assert_status, extract_uuid, json_body


class SafeUser(dict[str, Any]):
    """Данные пользователя с безопасным repr для pytest-отчётов."""

    def __repr__(self) -> str:
        return (
            "SafeUser("
            f"id={self.get('id')!r}, "
            f"username={self.get('username')!r}, "
            "password=<REDACTED>, token=<REDACTED>)"
        )


@pytest.fixture
def base_url() -> str:
    return os.getenv("BASE_URL", "https://qa-internship.avito.com")


@pytest.fixture
def client(base_url: str) -> Generator[ApiClient, None, None]:
    timeout = float(os.getenv("REQUEST_TIMEOUT", "15"))
    api = ApiClient(base_url, timeout)
    yield api
    api.session.close()


@pytest.fixture
def user_factory(client: ApiClient) -> Callable[..., SafeUser]:
    def create_user(
        username: str | None = None,
        password: str | None = None,
    ) -> SafeUser:
        suffix = uuid.uuid4().hex
        actual_username = username or f"qa_2026_{suffix}"
        actual_password = password or f"Qa!2026_{suffix}"

        register_response = client.register(actual_username, actual_password)
        assert_status(register_response, 201)
        registered = json_body(register_response)
        assert isinstance(registered, dict), "Регистрация должна возвращать JSON-объект"
        assert isinstance(registered.get("id"), int), "Поле id должно быть целым числом"
        assert registered.get("username") == actual_username, (
            "Регистрация должна вернуть переданный username"
        )

        auth_response = client.authorize(actual_username, actual_password)
        assert_status(auth_response, 200)
        authorized = json_body(auth_response)
        assert isinstance(authorized, dict), "Авторизация должна возвращать JSON-объект"
        token = authorized.get("accessToken")
        assert isinstance(token, str) and token, "accessToken должен быть непустой строкой"
        assert str(authorized.get("tokenType", "")).lower() == "bearer", (
            "tokenType должен быть Bearer"
        )
        return SafeUser(
            id=registered["id"],
            username=actual_username,
            password=actual_password,
            token=token,
        )

    return create_user


@pytest.fixture
def authorized_user(user_factory: Callable[..., SafeUser]) -> SafeUser:
    return user_factory()


@pytest.fixture
def item_factory(client: ApiClient):
    created: list[tuple[str, str]] = []

    def create_item(
        user: SafeUser,
        *,
        name: str | None = None,
        price: int = 9900,
        statistics: dict[str, int] | None = None,
        seller_id: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        payload = {
            "sellerID": user["id"] if seller_id is None else seller_id,
            "name": name or f"item_{uuid.uuid4().hex}",
            "price": price,
            "statistics": (
                statistics
                if statistics is not None
                else {"likes": 21, "viewCount": 11, "contacts": 43}
            ),
        }
        response = client.create_item(user["token"], payload, headers=headers)
        assert_status(response, 200)
        item_id = extract_uuid(response)
        created.append((user["token"], item_id))
        return item_id, payload

    def forget(item_id: str) -> None:
        created[:] = [(token, saved_id) for token, saved_id in created if saved_id != item_id]

    create_item.forget = forget  # type: ignore[attr-defined]
    yield create_item

    for token, item_id in reversed(created):
        try:
            client.delete_item(token, item_id)
        except Exception:
            # Ошибка очистки не должна маскировать основной результат теста.
            pass
