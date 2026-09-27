from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

RESULTS = Path("test-results.xml")
OUTPUT = Path("BUGS.md")
BASE_URL = "https://qa-internship.avito.com"
JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
PASSWORD_RE = re.compile(r"Qa!2026_[0-9a-f]{32}", re.IGNORECASE)


def sanitize(text: str) -> str:
    text = JWT_RE.sub("<REDACTED_TOKEN>", text)
    return PASSWORD_RE.sub("<REDACTED_PASSWORD>", text)


def failed_cases() -> list[tuple[str, str]]:
    if not RESULTS.exists():
        return []
    root = ET.parse(RESULTS).getroot()
    failures = []
    for case in root.iter("testcase"):
        problem = case.find("failure")
        if problem is None:
            problem = case.find("error")
        if problem is None:
            continue
        node = f"{case.attrib.get('classname', 'unknown')}::{case.attrib.get('name', 'unknown')}"
        details = sanitize(problem.text or problem.attrib.get("message", "Нет деталей"))
        failures.append((node, details.strip()))
    return failures


def add_bug(
    lines: list[str],
    bug_id: str,
    title: str,
    severity: str,
    preconditions: str,
    steps: list[str],
    actual: str,
    expected: str,
) -> None:
    lines.extend(
        [
            f"## {bug_id}: {title}",
            "",
            f"- **Серьёзность:** {severity}",
            f"- **Окружение:** `{BASE_URL}`",
            f"- **Предусловия:** {preconditions}",
            "- **Шаги воспроизведения:**",
        ]
    )
    lines.extend(f"  {index}. {step}" for index, step in enumerate(steps, start=1))
    lines.extend(
        [
            f"- **Фактический результат:** {actual}",
            f"- **Ожидаемый результат:** {expected}",
            "",
        ]
    )


def matched(nodes: list[str], fragment: str) -> list[str]:
    return [node for node in nodes if fragment in node]


def main() -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    failures = failed_cases()
    nodes = [node for node, _ in failures]
    known_nodes: set[str] = set()
    lines = [
        "# BUGS",
        "",
        f"Результат проверен автоматизированными тестами {timestamp}.",
        "",
    ]

    found = matched(nodes, "test_another_user_cannot_delete_owners_item")
    if found:
        known_nodes.update(found)
        add_bug(
            lines,
            "BUG-001",
            "пользователь может удалить чужое объявление",
            "Critical",
            "зарегистрированы и авторизованы два уникальных пользователя A и B.",
            [
                "Создать объявление от имени A с sellerID пользователя A.",
                "Отправить DELETE `/api/2/item/{id}` с bearer-токеном пользователя B.",
                "Получить объявление с bearer-токеном владельца A.",
            ],
            "DELETE возвращает HTTP 200, последующий GET владельца возвращает HTTP 404.",
            "Удаление отклоняется с HTTP 403/404; объявление остаётся доступно владельцу.",
        )

    found = matched(nodes, "test_create_item_accepts_zero_statistic_value")
    if found:
        known_nodes.update(found)
        variants = ", ".join(node.rsplit("[", 1)[-1].rstrip("]") for node in found)
        actual = (
            f"Для вариантов `{variants}` сервис возвращает HTTP 400 и сообщает, "
            "что соответствующее поле обязательно."
        )
        add_bug(
            lines,
            "BUG-002",
            "нулевое значение счётчика статистики воспринимается как отсутствующее поле",
            "Medium",
            "пользователь зарегистрирован и авторизован.",
            [
                "Подготовить валидное объявление с положительной ценой и счётчиками.",
                "Поочерёдно передать 0 в likes, viewCount и contacts.",
                "Отправить POST `/api/1/item` с валидным bearer-токеном.",
            ],
            actual,
            "Значение 0 принимается как переданное неотрицательное значение счётчика.",
        )

    found = matched(nodes, "test_statistic_v2_error_http_status_matches_body")
    if found:
        known_nodes.update(found)
        add_bug(
            lines,
            "BUG-003",
            "HTTP-статус ошибки statistic v2 не совпадает с полем status в JSON",
            "Medium",
            "пользователь зарегистрирован и авторизован.",
            [
                "Выполнить GET `/api/2/statistic/not-a-uuid` с валидным bearer-токеном.",
                "Сравнить HTTP-код ответа и поле `status` в JSON.",
            ],
            'HTTP-ответ имеет код 404, но тело содержит `"status": "400"`.',
            "HTTP-код и поле `status` согласованы и описывают одну ошибку.",
        )

    found = matched(nodes, "test_create_item_rejects_invalid_field_values[negative-price]")
    if found:
        known_nodes.update(found)
        add_bug(
            lines,
            "BUG-004",
            "сервис создаёт объявление с отрицательной ценой",
            "High",
            "пользователь зарегистрирован и авторизован.",
            [
                "Подготовить валидное объявление.",
                "Передать `price: -1`.",
                "Отправить POST `/api/1/item` с валидным bearer-токеном.",
            ],
            "Сервис возвращает HTTP 200 и создаёт объявление с UUID.",
            "Сервис отклоняет отрицательную цену с HTTP 400.",
        )

    found = matched(nodes, "test_create_item_rejects_invalid_field_values[negative-likes]")
    if found:
        known_nodes.update(found)
        add_bug(
            lines,
            "BUG-005",
            "сервис создаёт объявление с отрицательным количеством лайков",
            "Medium",
            "пользователь зарегистрирован и авторизован.",
            [
                "Подготовить валидное объявление.",
                "Передать `statistics.likes: -1`.",
                "Отправить POST `/api/1/item` с валидным bearer-токеном.",
            ],
            "Сервис возвращает HTTP 200 и создаёт объявление с UUID.",
            "Сервис отклоняет отрицательное значение счётчика с HTTP 400.",
        )

    unknown = [(node, details) for node, details in failures if node not in known_nodes]
    for index, (node, details) in enumerate(unknown, start=1):
        lines.extend(
            [
                f"## INVESTIGATION-{index:03d}: неожиданное падение `{node}`",
                "",
                "- **Статус:** требуется ручная проверка.",
                "- **Санитизированные детали:**",
                "",
                "```text",
                sanitize(details)[:1500],
                "```",
                "",
            ]
        )

    if not failures:
        lines.extend(["На текущем прогоне дефекты не воспроизвелись.", ""])

    OUTPUT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
