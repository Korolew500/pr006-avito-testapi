from __future__ import annotations

import re
import uuid
from typing import Any

import requests

UUID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
    re.IGNORECASE,
)
_UNSET = object()


class ApiClient:
    def __init__(self, base_url: str, timeout: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        headers: dict[str, str] | None = None,
        json_body: Any = _UNSET,
        data: str | bytes | None = None,
    ) -> requests.Response:
        request_headers = dict(headers or {})
        if token is not None:
            request_headers["Authorization"] = f"Bearer {token}"
        kwargs: dict[str, Any] = {
            "method": method,
            "url": f"{self.base_url}{path}",
            "headers": request_headers,
            "timeout": self.timeout,
        }
        if json_body is not _UNSET:
            kwargs["json"] = json_body
        if data is not None:
            kwargs["data"] = data
        return self.session.request(**kwargs)

    def register(self, username: str, password: str) -> requests.Response:
        return self.request(
            "POST",
            "/api/1/register",
            json_body={"username": username, "password": password},
        )

    def authorize(self, username: str, password: str) -> requests.Response:
        return self.request(
            "POST",
            "/api/1/autorize",
            json_body={"username": username, "password": password},
        )

    def create_item(
        self,
        token: str,
        payload: dict[str, Any],
        *,
        headers: dict[str, str] | None = None,
    ) -> requests.Response:
        return self.request("POST", "/api/1/item", token=token, headers=headers, json_body=payload)

    def get_item(self, token: str, item_id: str) -> requests.Response:
        return self.request("GET", f"/api/1/item/{item_id}", token=token)

    def get_seller_items(self, token: str, seller_id: int | str) -> requests.Response:
        return self.request("GET", f"/api/1/{seller_id}/item", token=token)

    def get_statistic(self, token: str, item_id: str, version: int = 1) -> requests.Response:
        return self.request("GET", f"/api/{version}/statistic/{item_id}", token=token)

    def delete_item(self, token: str, item_id: str) -> requests.Response:
        return self.request("DELETE", f"/api/2/item/{item_id}", token=token)


def response_details(response: requests.Response) -> str:
    body = response.text
    if len(body) > 1000:
        body = f"{body[:1000]}...[truncated]"
    return (
        f"method={response.request.method}, url={response.request.url}, "
        f"status={response.status_code}, body={body!r}"
    )


def assert_status(response: requests.Response, expected: int | set[int]) -> None:
    expected_set = {expected} if isinstance(expected, int) else set(expected)
    assert response.status_code in expected_set, (
        f"Ожидался HTTP {sorted(expected_set)}, получен другой ответ: {response_details(response)}"
    )


def json_body(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError as exc:
        raise AssertionError(f"Ответ не является JSON: {response_details(response)}") from exc


def extract_uuid(response: requests.Response) -> str:
    body = json_body(response)
    text = str(body.get("status", "")) if isinstance(body, dict) else str(body)
    match = UUID_PATTERN.search(text)
    assert match, f"В успешном ответе создания не найден UUID: {response_details(response)}"
    item_id = match.group(0)
    uuid.UUID(item_id)
    return item_id


def first_object(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list):
        assert payload, "Ожидался непустой массив объектов"
        payload = payload[0]
    assert isinstance(payload, dict), (
        f"Ожидался JSON-объект или массив объектов, получено: {payload!r}"
    )
    return payload


def field(data: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in data:
            return data[name]
    raise AssertionError(f"Ни одно из полей {names!r} не найдено в объекте {data!r}")


def normalize_statistics(payload: Any) -> dict[str, Any]:
    data = first_object(payload)
    nested = data.get("statistics")
    if isinstance(nested, dict):
        data = nested
    return {
        "likes": field(data, "likes"),
        "viewCount": field(data, "viewCount", "view_count"),
        "contacts": field(data, "contacts"),
    }
