"""README 의 프리셋 표가 config 의 PRESETS 와 맞는지 본다.

표의 `끄는 규칙` 칸은 손으로 관리하는 수가 아니라 검사되는 투영이다. 2026-09-02 에 일곱 가운데 넷 (guide,
report, docs, encyclopedia) 이 실제와 달랐다. 프리셋이 규칙을 얻거나 잃으면 여기서 빨개진다.
"""

from __future__ import annotations

import re
from pathlib import Path

from hanlint.config.settings import PRESETS

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
ROW = re.compile(r"^\| `([a-z]+)` \| [^|]+ \| (\d+)개 \| [^|]+ \|$")


def tableRows(text: str) -> dict[str, int]:
    """프리셋 이름 → README 가 말하는 끄는 규칙 수."""
    rows: dict[str, int] = {}
    for line in text.split("\n"):
        match = ROW.match(line.rstrip())
        if match:
            rows[match.group(1)] = int(match.group(2))
    return rows


def mismatches(text: str) -> dict[str, tuple[int, int]]:
    """프리셋 이름 → (README 의 수, PRESETS 의 수). 다른 것만 담는다."""
    return {
        name: (count, len(PRESETS[name]))
        for name, count in tableRows(text).items()
        if name in PRESETS and count != len(PRESETS[name])
    }


def testTableNamesEveryPreset() -> None:
    assert set(tableRows(README.read_text(encoding="utf-8"))) == set(PRESETS)


def testTableCountsMatchPresets() -> None:
    assert mismatches(README.read_text(encoding="utf-8")) == {}


def testCatchesWrongCount() -> None:
    assert mismatches("| `docs` | 참고 문서 | 3개 | 기술 문서 |") == {"docs": (3, len(PRESETS["docs"]))}


def testIgnoresOtherTables() -> None:
    assert tableRows("| `hanlint fix` | 고침 | 예 |\n| 이름 | 3개 | x | y |") == {}
