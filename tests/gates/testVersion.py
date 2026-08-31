"""버전 정본 게이트. 손으로 적는 버전은 `src/hanlint/__init__.py` 의 `__version__` 과
`npm/package.json` 둘뿐이고, `pyproject.toml` 은 hatch 가 `__version__` 을 읽는다 (dynamic).
`npm/data/version.json` 은 exportData 투영이다. 어긋나면 빨갛다.

0.0.2 릴리즈에서 pyproject 와 npm 만 올리고 `__version__` 을 빼먹어, 두 CLI 의 `--version` 이
0.0.1 을 찍은 채 게시됐다. 버전을 세 곳에 손으로 적는 구조가 원인이라 소유를 둘로 줄이고
이 게이트가 일치를 강제한다.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from hanlint import __version__

ROOT = Path(__file__).resolve().parents[2]


def testHandWrittenVersionsAgree():
    npmVersion = json.loads((ROOT / "npm" / "package.json").read_text(encoding="utf-8"))["version"]
    projection = json.loads((ROOT / "npm" / "data" / "version.json").read_text(encoding="utf-8"))["version"]
    assert __version__ == npmVersion == projection


def testNpmLockProjectsPackageVersion():
    npmVersion = json.loads((ROOT / "npm" / "package.json").read_text(encoding="utf-8"))["version"]
    lock = json.loads((ROOT / "npm" / "package-lock.json").read_text(encoding="utf-8"))
    assert lock["version"] == npmVersion
    assert lock["packages"][""]["version"] == npmVersion


def testPyprojectDelegatesToInit():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert "version" in project.get("dynamic", []), "pyproject 는 버전을 직접 들지 않고 hatch dynamic 으로 __version__ 을 읽는다"
    assert "version" not in project
