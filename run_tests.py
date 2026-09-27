from __future__ import annotations

import subprocess
import sys
from pathlib import Path

COMMAND = [
    sys.executable,
    "-m",
    "pytest",
    "-ra",
    "--tb=short",
    "--junitxml=test-results.xml",
    "--html=test-report.html",
    "--self-contained-html",
]


def main() -> int:
    completed = subprocess.run(COMMAND, check=False)
    Path("pytest-exit-code.txt").write_text(str(completed.returncode), encoding="utf-8")
    # 0 = всё прошло; 1 = тесты нашли дефекты. Оба кода означают корректный запуск pytest.
    if completed.returncode in {0, 1}:
        return 0
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
