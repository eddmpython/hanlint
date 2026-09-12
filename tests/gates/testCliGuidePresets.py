"""명령 안내의 프리셋 표가 config의 PRESETS와 맞는지 본다.

표의 `끄는 규칙` 칸은 손으로 관리하는 수가 아니라 검사되는 투영이다. 2026-09-02 에 일곱 가운데 넷 (guide,
report, docs, encyclopedia) 이 실제와 달랐다. 프리셋이 규칙을 얻거나 잃거나, 행이 빠지거나 겹치거나, 모르는
프리셋이 끼면 여기서 빨개진다.
"""

from __future__ import annotations

import re
from pathlib import Path

from hanlint.config.settings import PRESETS

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "skills" / "specs" / "start" / "cli.md"
ROW = re.compile(r"^\| `([a-z]+)` \| [^|]+ \| (\d+)개 \| [^|]+ \|$")
GOOD = {name: len(rules) for name, rules in PRESETS.items()}
"""PRESETS 가 말하는 프리셋별 끄는 규칙 수."""


def tableRows(text: str) -> list[tuple[str, int]]:
    """명령 안내 표의 (프리셋 이름, 끄는 규칙 수) 를 나온 순서대로."""
    rows: list[tuple[str, int]] = []
    for line in text.split("\n"):
        match = ROW.match(line.rstrip())
        if match:
            rows.append((match.group(1), int(match.group(2))))
    return rows


def problems(text: str) -> list[str]:
    """명령 안내 표와 PRESETS 의 어긋남. 비어 있어야 정상이다."""
    rows = tableRows(text)
    names = [name for name, _ in rows]
    found = [f"{name}: 행이 {names.count(name)}번 나온다" for name in sorted(set(names)) if names.count(name) > 1]
    found += [f"{name}: PRESETS 에 없는 프리셋" for name in sorted(set(names) - set(PRESETS))]
    found += [f"{name}: 행이 없다" for name in sorted(set(PRESETS) - set(names))]
    found += [
        f"{name}: 명령 안내 {count}개, PRESETS {GOOD[name]}개" for name, count in rows if name in GOOD and count != GOOD[name]
    ]
    return found


def table(counts: dict[str, int]) -> str:
    """시험용 명령 안내 표. 이름과 수만 뜻이 있다."""
    return "\n".join(f"| `{name}` | 글 | {count}개 | 프로파일 |" for name, count in counts.items())


def testGuideTableMatchesPresets() -> None:
    assert problems(GUIDE.read_text(encoding="utf-8")) == []


def testCatchesWrongCount() -> None:
    assert problems(table({**GOOD, "docs": 3})) == [f"docs: 명령 안내 3개, PRESETS {GOOD['docs']}개"]


def testCatchesMissingRow() -> None:
    rows = dict(GOOD)
    del rows["blog"]
    assert problems(table(rows)) == ["blog: 행이 없다"]


def testCatchesUnknownRow() -> None:
    assert problems(table({**GOOD, "news": 0})) == ["news: PRESETS 에 없는 프리셋"]


def testCatchesDuplicateRow() -> None:
    assert problems(table(GOOD) + "\n" + table({"docs": GOOD["docs"]})) == ["docs: 행이 2번 나온다"]


def testIgnoresOtherTables() -> None:
    assert tableRows("| `hanlint fix` | 고침 | 예 |\n| 이름 | 3개 | x | y |") == []
