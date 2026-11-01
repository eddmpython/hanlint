from __future__ import annotations

import re
from collections.abc import Iterator

from ...analysis.grammar import fitJosa
from ...config import Config
from ...fingerprint import DocumentPrint
from ...fingerprint.markers import matchedTexts, numeralsIn
from ..finding import NOTICE, SENTENCE, Finding
from ..registry import rule

RANGE = re.compile(r"([0-9][0-9,]*(?:\.[0-9]+)?)[^\s.!?]{0,4}\s?에서\s?([0-9][0-9,]*(?:\.[0-9]+)?)[^\s.!?]{0,4}\s?(?:로|으로)")
MIN_DIGITS = 2
"""한 자리 수는 재는 값이 아니라 세는 말이라 뺀다. 하나에서 둘로 는 측정이 아니다."""
ANCHOR_WINDOW = 12
"""기준값 앞 몇 글자에서 출처를 밝히는 말을 찾는가. `1년 전 26.14%에서` 가 들어오는 폭이다."""


def isMeasured(numeral: str) -> bool:
    return "." in numeral or len(numeral.replace(".", "")) >= MIN_DIGITS


def isAnchored(text: str, start: int) -> bool:
    """값 바로 앞이 그 값이 어디서 온 것인지 말하고 있는가."""
    return bool(matchedTexts(text[max(0, start - ANCHOR_WINDOW) : start], "baselineAnchors.txt"))


@rule("numberOrphan", mechanism="reader")
def numberOrphan(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """`A에서 B로`라고 비교하는데 A가 글 앞에 한 번도 나온 적 없는 경우.

    왜: 독자는 앞에서 본 값을 기준으로 변화를 읽는다. 기준값이 그 문장에서 처음 나오면 무엇에서 무엇으로
        움직인 것인지 알 수 없고, 앞으로 되돌아가 찾다가 없다는 것을 확인하고 멈춘다.
    어디서: 실측. 실제 블로그 글의 `이 5백만 줄 표를 넘길 때 파이썬이 잡은 메모리 최대치는 453MB에서 700MB로
        올라갔습니다`를 평가자가 지적했다. 453MB가 앞의 어떤 실행에도 없었다. 새로 나온 값과 옵션은 무엇인지,
        왜 그 값인지, 독자가 지금 무엇을 하면 되는지를 그 자리에서 알려 준다는 글쓰기 원칙.
    고치기: 기준값이 어디서 나온 것인지 한 문장으로 밝히거나, 그 값을 만든 실행을 앞에 둔다.
    안 잡는 것: 한 자리 수(재는 값이 아니라 세는 말이다). 앞선 문장, 코드 블록, 출력, 표, 목록, 제목에 이미
        나온 값. 같은 문장 안에서 앞서 나온 값. 값 바로 앞에서 그 값의 출처를 밝힌 경우(`1년 전 26.14%에서
        18.53%로`는 어디서 온 값인지 이미 말했다. 실측에서 오탐이었고 data/baselineAnchors.txt로 걸렀다).
        겉으로 보이는 글자로 어림해 세는 규칙이라 경고로만 낸다.
    """
    for sentence in doc.sentences:
        reader = doc.reader.beforeSentence[sentence.index]
        for match in RANGE.finditer(sentence.text):
            base = match.group(1).replace(",", "")
            if not isMeasured(base) or base == match.group(2).replace(",", ""):
                continue
            if base in reader.numerals or base in numeralsIn(sentence.text[: match.start()]):
                continue
            if isAnchored(sentence.text, match.start()):
                continue
            yield Finding(
                "numberOrphan",
                sentence.line,
                sentence.text,
                f"`{base}`{fitJosa(base, '가')} 여기서 처음 나오는 값이다. 무엇에서 올라간 것인지 알 수 없다. "
                "그 값이 어디서 나왔는지 밝힌다",
                None,
                NOTICE,
                SENTENCE,
                sentence.index,
            )
