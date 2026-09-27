from __future__ import annotations

import uuid

import pytest

from api_client import assert_status


@pytest.mark.security
@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        (
            "POST",
            "/api/1/item",
            {
                "sellerID": 1,
                "name": "no_auth",
                "price": 1,
                "statistics": {"likes": 0, "viewCount": 0, "contacts": 0},
            },
        ),
        ("GET", f"/api/1/item/{uuid.uuid4()}", None),
        ("GET", "/api/1/1/item", None),
        ("GET", f"/api/1/statistic/{uuid.uuid4()}", None),
        ("GET", f"/api/2/statistic/{uuid.uuid4()}", None),
        ("DELETE", f"/api/2/item/{uuid.uuid4()}", None),
    ],
)
def test_protected_endpoints_without_token_return_401(client, method, path, body):
    response = (
        client.request(method, path, json_body=body)
        if body is not None
        else client.request(method, path)
    )
    assert_status(response, 401)


@pytest.mark.security
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", f"/api/1/item/{uuid.uuid4()}"),
        ("GET", "/api/1/1/item"),
        ("GET", f"/api/1/statistic/{uuid.uuid4()}"),
        ("GET", f"/api/2/statistic/{uuid.uuid4()}"),
        ("DELETE", f"/api/2/item/{uuid.uuid4()}"),
    ],
)
def test_protected_endpoints_reject_invalid_token(client, method, path):
    response = client.request(method, path, token="invalid.jwt.token")
    assert_status(response, 401)


@pytest.mark.security
def test_x_user_id_cannot_bypass_bearer_auth(client, authorized_user):
    payload = {
        "sellerID": authorized_user["id"],
        "name": f"x_user_bypass_{uuid.uuid4().hex}",
        "price": 100,
        "statistics": {"likes": 1, "viewCount": 1, "contacts": 1},
    }
    response = client.request(
        "POST",
        "/api/1/item",
        headers={"X-UserId": str(authorized_user["id"])},
        json_body=payload,
    )
    assert_status(response, 401)


@pytest.mark.security
def test_cannot_create_item_for_another_seller(client, user_factory):
    token_owner = user_factory()
    foreign_seller = user_factory()
    payload = {
        "sellerID": foreign_seller["id"],
        "name": f"foreign_{uuid.uuid4().hex}",
        "price": 100,
        "statistics": {"likes": 1, "viewCount": 1, "contacts": 1},
    }

    response = client.create_item(token_owner["token"], payload)

    assert_status(response, {400, 401, 403})


@pytest.mark.security
def test_x_user_id_cannot_override_token_identity(client, user_factory):
    token_owner = user_factory()
    foreign_seller = user_factory()
    payload = {
        "sellerID": foreign_seller["id"],
        "name": f"override_{uuid.uuid4().hex}",
        "price": 100,
        "statistics": {"likes": 1, "viewCount": 1, "contacts": 1},
    }

    response = client.create_item(
        token_owner["token"],
        payload,
        headers={"X-UserId": str(foreign_seller["id"])},
    )

    assert_status(response, {400, 401, 403})


@pytest.mark.security
def test_another_user_cannot_delete_owners_item(client, user_factory, item_factory):
    owner = user_factory()
    another_user = user_factory()
    item_id, _ = item_factory(owner)

    deletion = client.delete_item(another_user["token"], item_id)
    owner_read = client.get_item(owner["token"], item_id)

    assert deletion.status_code in {403, 404} and owner_read.status_code == 200, (
        "Нарушено разграничение доступа: пользователь с чужим bearer-токеном смог удалить "
        f"объявление. DELETE={deletion.status_code}, последующий GET владельца="
        f"{owner_read.status_code}"
    )
