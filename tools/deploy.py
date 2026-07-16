"""Локальная поставка собранного пакета в каталог тестовой среды."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from zipfile import ZipFile


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: deploy.py ARTIFACT_DIR COMMIT")
    artifact_dir = Path(sys.argv[1]).resolve()
    commit = sys.argv[2]
    wheels = sorted(artifact_dir.rglob("cybercity_data-*.whl"))
    if len(wheels) != 1:
        raise SystemExit("ожидался один wheel cybercity-data")
    with ZipFile(wheels[0]) as archive:
        names = set(archive.namelist())
    if not any(
        name.endswith("cybercity_data/city_model/adapters/inbound/controllers/app.py")
        for name in names
    ):
        raise SystemExit("проверка готовности: CLI отсутствует в wheel")
    target = Path(".deploy/test") / commit
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(wheels[0], target / wheels[0].name)
    print(f"готовность: {target}")
    print("быстрая проверка: wheel содержит CLI")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
