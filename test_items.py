from __future__ import annotations

import uuid

import pytest

from api_client import assert_status, extract_uuid, field, first_object, json_body


def test_create_and_get_item_preserves_fields(client, authorized_user, item_factory):
    statistics = {"likes": 7, "viewCount": 13, "contacts": 2}
    item_id, expected = item_factory(authorized_user, price=12345, statistics=statistics)

    response = client.get_item(authorized_user["token"], item_id)

    assert_status(response, 200)
    item = first_object(json_body(response))
    assert str(field(item, "id")) == item_id
    assert field(item, "name") == expected["name"]
    assert field(item, "price") == expected["price"]
    assert int(field(item, "sellerID", "sellerId")) == expected["sellerID"]


def test_identical_payloads_receive_unique_uuids(client, authorized_user, item_factory):
    name = f"repeatable_{uuid.uuid4().hex}"
    first_id, _ = item_factory(authorized_user, name=name, price=500)
    second_id, _ = item_factory(authorized_user, name=name, price=500)

    assert first_id != second_id, "Каждое объявление должно получать уникальный UUID"


def test_get_all_seller_items_contains_created_items(client, authorized_user, item_factory):
    first_id, _ = item_factory(authorized_user)
    second_id, _ = item_factory(authorized_user)

    response = client.get_seller_items(authorized_user["token"], authorized_user["id"])

    assert_status(response, 200)
    items = json_body(response)
    assert isinstance(items, list)
    ids = {str(item.get("id")) for item in items if isinstance(item, dict)}
    assert {first_id, second_id}.issubset(ids)


def test_new_seller_has_empty_item_list(client, user_factory):
    user = user_factory()
    response = client.get_seller_items(user["token"], user["id"])
    assert_status(response, 200)
    assert json_body(response) == []


def test_get_nonexistent_item_returns_404(client, authorized_user):
    response = client.get_item(authorized_user["token"], str(uuid.uuid4()))
    assert_status(response, 404)


def test_get_item_with_malformed_uuid_returns_400(client, authorized_user):
    response = client.get_item(authorized_user["token"], "not-a-uuid")
    assert_status(response, 400)


@pytest.mark.parametrize("missing_field", ["sellerID", "name", "price", "statistics"])
def test_create_item_without_required_field_returns_400(client, authorized_user, missing_field):
    payload = {
        "sellerID": authorized_user["id"],
        "name": f"missing_{uuid.uuid4().hex}",
        "price": 100,
        "statistics": {"likes": 1, "viewCount": 1, "contacts": 1},
    }
    payload.pop(missing_field)

    response = client.create_item(authorized_user["token"], payload)

    assert_status(response, 400)


def test_minimum_positive_values_are_accepted(client, authorized_user, item_factory):
    item_id, _ = item_factory(
        authorized_user,
        price=1,
        statistics={"likes": 1, "viewCount": 1, "contacts": 1},
    )
    assert uuid.UUID(item_id)


def test_zero_price_is_rejected_by_validation(client, authorized_user):
    payload = {
        "sellerID": authorized_user["id"],
        "name": f"zero_price_{uuid.uuid4().hex}",
        "price": 0,
        "statistics": {"likes": 1, "viewCount": 1, "contacts": 1},
    }

    response = client.create_item(authorized_user["token"], payload)

    assert_status(response, 400)
    assert "price" in response.text.lower(), "Ответ должен указывать на ошибку поля price"


@pytest.mark.parametrize(
    "field_name",
    ["likes", "viewCount", "contacts"],
    ids=["likes-zero", "view-count-zero", "contacts-zero"],
)
def test_create_item_accepts_zero_statistic_value(client, authorized_user, field_name):
    statistics = {"likes": 1, "viewCount": 1, "contacts": 1}
    statistics[field_name] = 0
    payload = {
        "sellerID": authorized_user["id"],
        "name": f"zero_{field_name}_{uuid.uuid4().hex}",
        "price": 100,
        "statistics": statistics,
    }

    response = client.create_item(authorized_user["token"], payload)

    assert_status(response, 200)
    item_id = extract_uuid(response)
    try:
        assert uuid.UUID(item_id)
    finally:
        client.delete_item(authorized_user["token"], item_id)


@pytest.mark.parametrize(
    "payload_change",
    [
        {"price": -1},
        {"name": ""},
        {"price": "100"},
        {"statistics": {"likes": -1, "viewCount": 1, "contacts": 1}},
        {"statistics": {"likes": 1, "viewCount": "1", "contacts": 1}},
    ],
    ids=[
        "negative-price",
        "empty-name",
        "string-price",
        "negative-likes",
        "string-view-count",
    ],
)
def test_create_item_rejects_invalid_field_values(client, authorized_user, payload_change):
    payload = {
        "sellerID": authorized_user["id"],
        "name": f"invalid_{uuid.uuid4().hex}",
        "price": 100,
        "statistics": {"likes": 1, "viewCount": 1, "contacts": 1},
    }
    payload.update(payload_change)

    response = client.create_item(authorized_user["token"], payload)
    unexpected_item_id = extract_uuid(response) if response.status_code == 200 else None

    try:
        assert_status(response, 400)
    finally:
        if unexpected_item_id is not None:
            client.delete_item(authorized_user["token"], unexpected_item_id)


def test_create_response_contains_valid_uuid(client, authorized_user):
    payload = {
        "sellerID": authorized_user["id"],
        "name": f"uuid_{uuid.uuid4().hex}",
        "price": 100,
        "statistics": {"likes": 1, "viewCount": 1, "contacts": 1},
    }
    response = client.create_item(authorized_user["token"], payload)
    assert_status(response, 200)
    item_id = extract_uuid(response)
    try:
        assert uuid.UUID(item_id)
    finally:
        client.delete_item(authorized_user["token"], item_id)
