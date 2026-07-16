"""Установка и быстрая проверка собранного CLI в тестовом окружении."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: deploy.py ARTIFACT_DIR COMMIT")
    artifact_dir = Path(sys.argv[1]).resolve()
    commit = sys.argv[2].strip()
    wheels = sorted(artifact_dir.rglob("cybercity_data-*.whl"))
    if not commit or len(wheels) != 1:
        raise SystemExit("ожидались непустой commit и один wheel cybercity-data")

    target = Path(".deploy/test") / commit
    if target.exists():
        shutil.rmtree(target)
    run(["uv", "venv", str(target)])
    scripts = target / ("Scripts" if sys.platform == "win32" else "bin")
    executable = scripts / ("cybercity-data.exe" if sys.platform == "win32" else "cybercity-data")
    python = scripts / ("python.exe" if sys.platform == "win32" else "python")
    run(["uv", "pip", "install", "--python", str(python), str(wheels[0])])
    completed = subprocess.run(
        [str(executable), "--help"], check=True, capture_output=True, text=True
    )
    if "check" not in completed.stdout or "build" not in completed.stdout:
        raise SystemExit("быстрая проверка CLI не обнаружила команды check/build")
    print(f"cybercity-data {commit}: установка, готовность и быстрая проверка успешны")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
