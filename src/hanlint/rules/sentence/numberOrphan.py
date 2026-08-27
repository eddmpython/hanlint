from __future__ import annotations

import re
from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ...fingerprint.markers import matchedTexts
from ..finding import NOTICE, SENTENCE, Finding
from ..registry import rule

NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
RANGE = re.compile(r"(\d[\d,]*(?:\.\d+)?)[^\s.!?]{0,4}\s?에서\s?(\d[\d,]*(?:\.\d+)?)[^\s.!?]{0,4}\s?(?:로|으로)")
MIN_DIGITS = 2
"""한 자리 수는 재는 값이 아니라 세는 말이라 뺀다. 하나에서 둘로 는 측정이 아니다."""
ANCHOR_WINDOW = 12
"""기준값 앞 몇 글자에서 출처를 밝히는 말을 찾는가. `1년 전 26.14%에서` 가 들어오는 폭이다."""


def numeralsIn(text: str) -> set[str]:
    return {match.group(0).replace(",", "") for match in NUMBER.finditer(text)}


def isMeasured(numeral: str) -> bool:
    return "." in numeral or len(numeral.replace(".", "")) >= MIN_DIGITS


def isAnchored(text: str, start: int) -> bool:
    """값 바로 앞이 그 값이 어디서 온 것인지 말하고 있는가."""
    return bool(matchedTexts(text[max(0, start - ANCHOR_WINDOW) : start], "baselineAnchors.txt"))


@rule("numberOrphan")
def numberOrphan(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """A 에서 B 로 라고 견주는데 A 가 글 앞에 한 번도 나온 적 없는 자리.

    왜: 독자는 앞에서 본 값을 기준으로 변화를 읽는다. 기준값이 그 자리에서 처음 나오면 무엇에서 무엇으로
        움직인 것인지 알 수 없고, 앞으로 되돌아가 찾다가 없다는 것을 확인하고 멈춘다.
    어디서: 실측. 블로그 004 의 `이 5백만 줄 표를 넘길 때 파이썬이 잡은 메모리 최대치는 453MB 에서 700MB 로
        올라갔습니다` 를 평가자가 집었다. 453MB 가 앞의 어떤 실행에도 없었다. cinch 의 전역 blog-writing 스킬,
        새로 나온 값과 옵션은 무엇인지 왜 그 값인지 독자가 지금 무엇을 하면 되는지를 그 자리에서 준다.
    고치기: 기준값이 어디서 나온 것인지 한 문장으로 밝히거나, 그 값을 만든 실행을 앞에 둔다.
    안 잡는 것: 한 자리 수 (세는 말이지 재는 값이 아니다). 앞선 문장, 코드 블록, 출력, 표, 목록, 제목에 이미
        나온 값. 같은 문장 안에서 앞서 나온 값. 값 바로 앞이 그 값의 출처를 밝히는 자리 (`1년 전 26.14% 에서
        18.53% 로` 는 어디서 온 값인지 이미 말했다. 실측 오탐이었고 data/baselineAnchors.txt 로 걸렀다).
        표층으로 세는 근사라 notice 로만 낸다.
    """
    seen: set[str] = set()
    pending = sorted((b for b in doc.blocks if not b.isProse), key=lambda b: (b.startLine, b.index))
    position = 0
    for sentence in doc.sentences:
        while position < len(pending) and pending[position].startLine < sentence.line:
            seen |= numeralsIn(pending[position].text)
            position += 1
        for match in RANGE.finditer(sentence.text):
            base = match.group(1).replace(",", "")
            if not isMeasured(base) or base == match.group(2).replace(",", ""):
                continue
            if base in seen or base in numeralsIn(sentence.text[: match.start()]):
                continue
            if isAnchored(sentence.text, match.start()):
                continue
            yield Finding(
                "numberOrphan",
                sentence.line,
                sentence.text,
                f"`{base}` 가 여기서 처음 나오는 값이다. 무엇에서 올라간 것인지 알 수 없다. 그 값이 어디서 나왔는지 밝힌다",
                None,
                NOTICE,
                SENTENCE,
                sentence.index,
            )
        seen |= numeralsIn(sentence.text)
