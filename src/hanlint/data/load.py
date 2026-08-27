"""data 폴더의 파일을 읽는 세 함수. 한 번 읽은 것은 기억한다.

- `loadLines`: 한 줄에 항목 하나. `#` 으로 시작하면 주석, 빈 줄은 무시
- `loadPatterns`: 한 줄에 정규식 하나. 컴파일해서 준다
- `loadToml`: `[[entry]]` 목록을 가진 사전
"""

from __future__ import annotations

import re
import tomllib
from functools import cache
from importlib import resources


def readText(name: str) -> str:
    return resources.files("hanlint.data").joinpath(name).read_text(encoding="utf-8")


@cache
def loadLines(name: str) -> tuple[str, ...]:
    lines = []
    for line in readText(name).splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            lines.append(stripped)
    return tuple(lines)


@cache
def loadPatterns(name: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(line) for line in loadLines(name))


@cache
def loadToml(name: str, key: str = "entry") -> tuple[dict, ...]:
    """`[[key]]` 목록을 준다. 사전은 entry, 구멍 종류는 kind 다."""
    data = tomllib.loads(readText(name))
    return tuple(data.get(key, []))
