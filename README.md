# Автотесты API — задание 2.1

Проект проверяет сервис пользователей, объявлений и статистики на стенде
`https://qa-internship.avito.com`.

## Стек

- Python 3.10+
- pytest + requests
- pytest-html — HTML-отчёт
- Ruff — линтер и форматтер

## Состав проекта

- `api_client.py` — HTTP-клиент и общие assert-проверки.
- `conftest.py` — динамические пользователи, bearer-токены, объявления и cleanup.
- `test_*.py` — позитивные, негативные, граничные, security-, E2E- и нефункциональные тесты.
- `TESTCASES.md` — тест-кейсы и матрица покрытия.
- `BUGS.md` — дефекты, воспроизведённые автотестами.
- `PROMPTS.md` — использованные промпты без секретов.
- `test-report.html` — пример отчёта последнего прогона.

## Установка

```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Настройка

```bat
set BASE_URL=https://qa-internship.avito.com
set REQUEST_TIMEOUT=15
set MAX_RESPONSE_TIME_MS=5000
```

Переменные необязательны: эти значения используются по умолчанию.

## Запуск

```bat
python -m pytest -ra --tb=short --junitxml=test-results.xml --html=test-report.html --self-contained-html
python generate_bugs.py
python check_no_secrets.py
python validate_results.py
```

Код pytest `1` допустим, если тест воспроизвёл дефект и падение связано с записью в
`BUGS.md`. Неожиданных падений со статусом `INVESTIGATION` перед отправкой быть не должно.

## Линтер и форматтер

```bat
python -m ruff format --check api_client.py conftest.py generate_bugs.py run_tests.py check_no_secrets.py validate_results.py
python -m ruff check api_client.py conftest.py generate_bugs.py run_tests.py check_no_secrets.py validate_results.py
```

## Независимость и очистка

Каждый тест создаёт уникального пользователя и получает токен через `/api/1/autorize`.
Объявления удаляются после тестов, в том числе если сервис неожиданно принял невалидные
данные. Удалить пользователей невозможно: такой ручки в контракте нет.

## Дефекты последнего прогона

На стенде воспроизводятся проверки:

1. удаление чужого объявления;
2. отклонение нулевых счётчиков как отсутствующих полей;
3. рассогласование HTTP-кода и `body.status` у statistic v2;
4. принятие отрицательной цены;
5. принятие отрицательного количества лайков.

Подробные шаги и серьёзность указаны в `BUGS.md`.

## Безопасность

`SafeUser` скрывает пароли и bearer-токены в pytest-отчётах. Скрипт
`check_no_secrets.py` проверяет HTML, XML и `BUGS.md` на наличие JWT и динамических паролей.
