from __future__ import annotations

import uuid

import pytest

from api_client import assert_status, json_body, normalize_statistics


@pytest.mark.parametrize("version", [1, 2])
def test_statistic_versions_return_created_values(client, authorized_user, item_factory, version):
    expected = {"likes": 17, "viewCount": 29, "contacts": 5}
    item_id, _ = item_factory(authorized_user, statistics=expected)

    response = client.get_statistic(authorized_user["token"], item_id, version)

    assert_status(response, 200)
    assert normalize_statistics(json_body(response)) == expected


def test_statistic_v1_and_v2_are_consistent(client, authorized_user, item_factory):
    expected = {"likes": 3, "viewCount": 8, "contacts": 1}
    item_id, _ = item_factory(authorized_user, statistics=expected)

    v1 = client.get_statistic(authorized_user["token"], item_id, 1)
    v2 = client.get_statistic(authorized_user["token"], item_id, 2)

    assert_status(v1, 200)
    assert_status(v2, 200)
    assert normalize_statistics(json_body(v1)) == normalize_statistics(json_body(v2))


@pytest.mark.parametrize("version", [1, 2])
def test_statistic_for_nonexistent_item_returns_404(client, authorized_user, version):
    response = client.get_statistic(authorized_user["token"], str(uuid.uuid4()), version)
    assert_status(response, 404)


def test_statistic_v1_with_malformed_uuid_returns_400(client, authorized_user):
    response = client.get_statistic(authorized_user["token"], "not-a-uuid", 1)
    assert_status(response, 400)


def test_statistic_v2_error_http_status_matches_body(client, authorized_user):
    response = client.get_statistic(authorized_user["token"], "not-a-uuid", 2)
    assert response.status_code in {400, 404}, (
        f"Некорректный UUID не должен приводить к 2xx/5xx, получен {response.status_code}"
    )
    body = json_body(response)
    assert isinstance(body, dict) and "status" in body, (
        "Ошибка должна возвращать JSON-объект с полем status"
    )
    assert str(body["status"]) == str(response.status_code), (
        "HTTP-статус не совпадает со статусом в JSON: "
        f"HTTP={response.status_code}, body.status={body['status']!r}, body={body!r}"
    )


def test_delete_item_then_item_is_unavailable(client, authorized_user, item_factory):
    item_id, _ = item_factory(authorized_user)

    deletion = client.delete_item(authorized_user["token"], item_id)

    assert_status(deletion, 200)
    item_factory.forget(item_id)
    assert_status(client.get_item(authorized_user["token"], item_id), 404)


def test_delete_nonexistent_item_returns_404(client, authorized_user):
    response = client.delete_item(authorized_user["token"], str(uuid.uuid4()))
    assert_status(response, 404)


def test_delete_item_with_malformed_uuid_returns_400(client, authorized_user):
    response = client.delete_item(authorized_user["token"], "not-a-uuid")
    assert_status(response, 400)


@pytest.mark.e2e
def test_full_user_item_lifecycle(client, user_factory, item_factory):
    user = user_factory()
    expected_statistics = {"likes": 9, "viewCount": 27, "contacts": 4}
    item_id, expected_item = item_factory(
        user,
        name=f"e2e_{uuid.uuid4().hex}",
        price=777,
        statistics=expected_statistics,
    )

    item_response = client.get_item(user["token"], item_id)
    assert_status(item_response, 200)
    assert expected_item["name"] in item_response.text

    for version in (1, 2):
        statistics_response = client.get_statistic(user["token"], item_id, version)
        assert_status(statistics_response, 200)
        assert normalize_statistics(json_body(statistics_response)) == expected_statistics

    seller_items = client.get_seller_items(user["token"], user["id"])
    assert_status(seller_items, 200)
    assert item_id in seller_items.text

    assert_status(client.delete_item(user["token"], item_id), 200)
    item_factory.forget(item_id)
    assert_status(client.get_item(user["token"], item_id), 404)
