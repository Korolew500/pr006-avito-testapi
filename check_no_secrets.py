from __future__ import annotations

import re
from pathlib import Path

FILES = [Path("BUGS.md"), Path("test-results.xml"), Path("test-report.html")]
PATTERNS = {
    "JWT": re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
    "generated password": re.compile(r"Qa!2026_[0-9a-f]{32}", re.IGNORECASE),
}


def main() -> int:
    findings = []
    for path in FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for label, pattern in PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{path}: найден {label}")
    if findings:
        print("Обнаружены секреты в отчётах:")
        print("\n".join(findings))
        return 1
    print("Проверка пройдена: JWT и сгенерированные пароли в отчётах не найдены.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
