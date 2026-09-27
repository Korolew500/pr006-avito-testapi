from __future__ import annotations

from pathlib import Path


def main() -> int:
    bugs = Path("BUGS.md")
    report = Path("test-report.html")
    exit_code = Path("pytest-exit-code.txt")

    missing = [str(path) for path in (bugs, report, exit_code) if not path.exists()]
    if missing:
        print(f"Не созданы обязательные результаты: {', '.join(missing)}")
        return 1

    content = bugs.read_text(encoding="utf-8")
    if "INVESTIGATION-" in content:
        print("В BUGS.md остались неожиданные падения со статусом INVESTIGATION.")
        return 1

    code = exit_code.read_text(encoding="utf-8").strip()
    if code not in {"0", "1"}:
        print(f"Некорректный код запуска pytest: {code!r}")
        return 1

    print("Результаты согласованы: неожиданных падений нет, обязательные отчёты созданы.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
