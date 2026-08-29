"""문장에서 표지를 센다. 종결어미 부류, 서법, 접속부사, 인과, 지시어, 헤지, 약속과 회수, 독자 호출, 수 약속, 수의 정체.

낱말 목록은 전부 data/ 가 정본이다. 여기는 그것을 읽어 세는 함수뿐이다.
"""

from __future__ import annotations

import re
from functools import cache

from ..data import loadLines, loadPatterns

TRAILING = re.compile(r"[\s.?!\"'”’)\]]+$")
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
NUMERAL = re.compile(r"\d[\d,]*(?:\.\d+)?")
"""값으로 견주는 수. NUMBER 는 수의 개수를 세고 (countNumbers) 이것은 수의 정체를 센다 (numeralsIn).
천 단위 쉼표까지 한 수로 읽고 numeralsIn 이 쉼표를 뗀다. 453MB 와 453 이 같은 값이어야 한다."""
COMMA = re.compile(r",")
# 따옴표 쌍. 안은 사용이 아니라 인용이다. 작은따옴표는 앞이 문장 첫머리나 공백이나 여는 괄호일 때만 (Python's 의 ' 는 아니다).
QUOTE_PAIRS = (
    re.compile(r'"([^"\n]{1,80})"'),
    re.compile(r"“([^“”\n]{1,80})”"),
    re.compile(r"‘([^‘’\n]{1,80})’"),
    re.compile(r"「([^「」\n]{1,80})」"),
    re.compile(r"『([^『』\n]{1,80})』"),
    re.compile(r"(?:(?<=^)|(?<=[\s(]))'([^'\n]{1,80})'"),
)


@cache
def koreanNumbers() -> dict[str, int]:
    """수사 → 값. 정본은 data/koreanNumbers.txt 이고 표층 분석기의 명사 나열도 같은 파일을 읽는다."""
    numbers: dict[str, int] = {}
    for line in loadLines("koreanNumbers.txt"):
        word, _, value = line.partition("\t")
        numbers[word] = int(value)
    return numbers


@cache
def endingClasses() -> tuple[tuple[str, re.Pattern[str]], ...]:
    classes = []
    for line in loadLines("endings.txt"):
        kind, _, pattern = line.partition("\t")
        classes.append((kind, re.compile(pattern)))
    return tuple(classes)


@cache
def connectorPattern() -> re.Pattern[str]:
    names = sorted(loadLines("connectors.txt"), key=len, reverse=True)
    return re.compile(r"^(" + "|".join(map(re.escape, names)) + r")(?=[\s,])")


@cache
def countPromisePattern() -> re.Pattern[str]:
    units = "|".join(map(re.escape, loadLines("countUnits.txt")))
    numbers = "|".join(sorted(koreanNumbers(), key=len, reverse=True))
    # 단위 뒤에는 조사가 붙는 것이 정상이다 (여섯 가지를). 앞쪽만 경계를 본다.
    return re.compile(rf"(?<![가-힣])({numbers}|\d+)\s?({units})")


def stripTrailing(text: str) -> str:
    return TRAILING.sub("", text.strip())


def endingOf(text: str) -> str:
    body = stripTrailing(text)
    for kind, pattern in endingClasses():
        if pattern.search(body):
            return kind
    return "없음"


def moodOf(text: str, ending: str) -> str:
    stripped = text.strip()
    if stripped.endswith("?") or ending == "의문":
        return "의문"
    if ending == "명령":
        return "명령"
    return "평서"


def connectorStartOf(text: str) -> str | None:
    match = connectorPattern().match(text.strip())
    return match.group(1) if match else None


def countMatches(text: str, patternFile: str) -> int:
    return sum(len(pattern.findall(text)) for pattern in loadPatterns(patternFile))


def matchedTexts(text: str, patternFile: str) -> tuple[str, ...]:
    found: list[str] = []
    for pattern in loadPatterns(patternFile):
        found.extend(match.group(0) for match in pattern.finditer(text))
    return tuple(found)


def matchedSpans(text: str, patternFile: str) -> tuple[tuple[int, int, str], ...]:
    """(시작, 끝, 원문). 인용 구간 안의 것을 거를 때 쓴다."""
    found: list[tuple[int, int, str]] = []
    for pattern in loadPatterns(patternFile):
        found.extend((match.start(), match.end(), match.group(0)) for match in pattern.finditer(text))
    return tuple(found)


def quoteSpans(text: str) -> tuple[tuple[int, int], ...]:
    """따옴표 쌍 안의 (시작, 끝). 인용은 사용이 아니다."""
    found: list[tuple[int, int]] = []
    for pattern in QUOTE_PAIRS:
        found.extend((match.start(1), match.end(1)) for match in pattern.finditer(text))
    return tuple(sorted(found))


def insideAny(start: int, end: int, spans: tuple[tuple[int, int], ...]) -> bool:
    return any(spanStart <= start and end <= spanEnd for spanStart, spanEnd in spans)


def countPromisesIn(text: str) -> tuple[tuple[int, str, str], ...]:
    found = []
    for match in countPromisePattern().finditer(text):
        raw, unit = match.group(1), match.group(2)
        if raw.isdigit() and unit == "단계" and " " not in match.group(0):
            # `3단계` 는 셋째 단계 (서수) 지 단계 셋의 약속이 아니다. 실측: 002 의 `여덟 단계` 와 `3단계` 가 충돌로 잡혔다.
            continue
        number = koreanNumbers().get(raw) or int(raw)
        found.append((number, unit, match.group(0)))
    return tuple(found)


def numeralsIn(text: str) -> frozenset[str]:
    """글에 나온 수의 정체 (천 단위 쉼표를 뗀 꼴). 독자 상태가 쌓고 numberOrphan 이 견준다."""
    return frozenset(match.group(0).replace(",", "") for match in NUMERAL.finditer(text))


def countNumbers(text: str) -> int:
    return len(NUMBER.findall(text))


def countCommas(text: str) -> int:
    return len(COMMA.findall(text))
