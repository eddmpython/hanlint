from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import DOCUMENT, Finding
from ..registry import rule


def sectionIndexAt(doc: DocumentPrint, line: int) -> int:
    index = 0
    for section in doc.sections:
        if section.startLine <= line:
            index = section.index
    return index


def comparable(doc: DocumentPrint, lineA: int, lineB: int) -> bool:
    """같은 절 안이거나, 도입과 마지막 절 사이일 때만 같은 목록을 센다고 본다."""
    a, b = sectionIndexAt(doc, lineA), sectionIndexAt(doc, lineB)
    last = doc.sections[-1].index
    return a == b or {a, b} == {0, last}


@rule("countMismatch", mechanism="contrast")
def countMismatch(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """같은 단위로 서로 다른 수를 약속하는 글. 여섯 가지를 소개한다고 열고 다섯 가지라고 닫는 것.

    왜: 독자는 어느 쪽을 믿어야 할지 모른다. 약속과 이행이 어긋난 글은 나머지도 의심받는다.
    어디서: 실측. 블로그 004 가 도입에서 여섯 방식을 약속하고 결말에서 다섯 가지라고 적었고 사람 평가자가
        네 라운드 내내 집었다. 이런 검사를 하는 선행 도구가 없다 (조사 결과). 단위 목록은 data/countUnits.txt.
    고치기: 수를 맞추거나, 서로 다른 것을 세는 문장이면 무엇을 세는지 이름을 붙인다.
    안 잡는 것: 단위가 다른 수 (여섯 가지 와 다섯 열). 같은 수의 반복. 서로 다른 본문 절에 있는 수 (둘째 절의
        두 가지 와 넷째 절의 네 가지 는 다른 목록이다. 실측: 002). 같은 절 안이거나 도입과 마지막 절 사이만
        견준다. `3단계` 처럼 숫자가 붙은 단계는 서수라 세지 않는다.
    """
    byUnit: dict[str, list[tuple[int, int, str]]] = defaultdict(list)
    for number, unit, line, text in doc.countPromises:
        byUnit[unit].append((line, number, text))
    for promises in byUnit.values():
        promises.sort()
        for i, (lineA, numberA, textA) in enumerate(promises):
            conflict = next(
                (p for p in promises[i + 1 :] if p[1] != numberA and comparable(doc, lineA, p[0])),
                None,
            )
            if conflict is None:
                continue
            lineB, _, textB = conflict
            yield Finding(
                "countMismatch",
                lineB,
                textB,
                f"{lineA}번째 줄은 `{textA}` 인데 여기는 `{textB}` 다. 같은 단위로 다른 수를 약속하면 "
                "독자가 어느 쪽을 믿을지 모른다",
                None,
                "error",
                DOCUMENT,
                -1,
            )
            break
