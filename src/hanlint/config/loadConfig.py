"""설정 파일을 찾아 읽는다. `hanlint.toml` 이거나 `pyproject.toml` 의 `[tool.hanlint]` 다."""

from __future__ import annotations

import tomllib
from pathlib import Path

from .settings import Config

CONFIG_NAME = "hanlint.toml"
PYPROJECT_NAME = "pyproject.toml"


def readConfigFile(path: Path) -> Config:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    if path.name == PYPROJECT_NAME:
        data = data.get("tool", {}).get("hanlint", {})
    config = Config.fromMapping(data)
    config.source = str(path)
    return config


def findConfigFile(start: Path) -> Path | None:
    """start 에서 위로 올라가며 hanlint.toml 이나 [tool.hanlint] 를 가진 pyproject.toml 을 찾는다."""
    for folder in (start, *start.parents):
        candidate = folder / CONFIG_NAME
        if candidate.exists():
            return candidate
        pyproject = folder / PYPROJECT_NAME
        if pyproject.exists():
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            if "hanlint" in data.get("tool", {}):
                return pyproject
    return None


def loadConfig(path: str | Path | None = None, start: str | Path | None = None) -> Config:
    """`path` 를 주면 그 파일만 읽는다. 안 주면 `start` (기본 현재 폴더) 에서 찾고, 없으면 기본값이다."""
    if path is not None:
        return readConfigFile(Path(path))
    found = findConfigFile(Path(start or Path.cwd()).resolve())
    return readConfigFile(found) if found else Config()
