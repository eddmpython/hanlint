from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator

from ...analysis.grammar import fitJosa
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


def blockIndexAt(doc: DocumentPrint, line: int) -> int:
    """줄이 든 문단의 차례. sectionIndexAt 과 같은 꼴로 훑는다."""
    index = 0
    for block in doc.blocks:
        if block.startLine <= line:
            index = block.index
    return index


def comparable(doc: DocumentPrint, lineA: int, lineB: int, span: int) -> bool:
    """도입의 약속과 마지막 절의 결산만 같은 목록으로 본다. 절이 없으면 첫 문단과 마지막 문단이 그 자리다.

    같은 절 안의 두 수도 견줬더니 백과와 수필에서 한 절이 목록 여럿을 담아 표본 20건 가운데 11건이 오탐이었다
    (2026-08-29). 약속과 결산이라는 꼴 (실측 004) 만 남긴다.

    절이 없는 글에서 span 줄만 재고 자리를 안 보던 때는 한 문장 안의 대조까지 잡았다. 실측: `흔히 말하는
    세 가지 방법이 아니라 네 가지 방법이 있다` 가 error 였고 지적문이 자기 줄을 가리켰다 (2026-08-31).
    """
    a, b = sectionIndexAt(doc, lineA), sectionIndexAt(doc, lineB)
    last = doc.sections[-1].index
    if last == 0:
        # 절이 없는 글은 짧을 때만 전체가 도입이자 결산이다. 긴 수필과 소설의 한 가지, 세 가지 는 목록 약속이 아니다.
        if max(block.endLine for block in doc.blocks) > span:
            return False
        # 한 문단 (한 문장 포함) 안의 두 수는 대조이지 두 번의 약속이 아니다. 첫 문단과 마지막 문단만 견준다.
        lastBlock = doc.blocks[-1].index
        return lastBlock != 0 and blockIndexAt(doc, lineA) == 0 and blockIndexAt(doc, lineB) == lastBlock
    return {a, b} == {0, last}


@rule("countMismatch", mechanism="contrast")
def countMismatch(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """같은 단위로 서로 다른 수를 약속하는 글. 여섯 가지를 소개한다고 열고 다섯 가지라고 닫는 것.

    왜: 독자는 어느 쪽을 믿어야 할지 모른다. 약속과 이행이 어긋난 글은 나머지도 의심받는다.
    어디서: 실제 블로그 글 하나가 도입에서 여섯 방식을 약속하고 결말에서 다섯 가지라고 적었고, 사람 평가자가
        네 차례 검토에서 모두 짚었다. 이런 검사를 하는 다른 도구는 찾지 못했다. 단위 목록은 data/countUnits.txt에 있다.
    고치기: 수를 맞추거나, 서로 다른 것을 세는 문장이면 무엇을 세는지 이름을 붙인다.
    안 잡는 것: 단위가 다른 수(`여섯 가지`와 `다섯 열`)와 같은 수의 반복은 잡지 않는다. 본문 절 안의 수도 잡지
        않는다. 둘째 절의 `두 가지`와 넷째 절의 `네 가지`는 다른 목록이다. 같은 절 안의 두 수까지 비교하자 백과사전과
        수필에서 표본 20건 가운데 11건이 오탐이었다. 그래서 도입의 약속과 마지막 절의 결산만 비교하고, 절이 없는 글은
        글 전체가 60줄 안일 때만 비교한다(설정 countMismatchSpan). `3단계`처럼 숫자가 붙은 단계는 서수라 세지 않는다.
    """
    byUnit: dict[str, list[tuple[int, int, str]]] = defaultdict(list)
    for number, unit, line, text in doc.countPromises:
        byUnit[unit].append((line, number, text))
    for promises in byUnit.values():
        promises.sort()
        for i, (lineA, numberA, textA) in enumerate(promises):
            conflict = next(
                (p for p in promises[i + 1 :] if p[1] != numberA and comparable(doc, lineA, p[0], config.countMismatchSpan)),
                None,
            )
            if conflict is None:
                continue
            lineB, _, textB = conflict
            yield Finding(
                "countMismatch",
                lineB,
                textB,
                f"{lineA}번째 줄은 `{textA}`{fitJosa(textA, '이라고')} 했는데 여기서는 `{textB}`{fitJosa(textB, '이라고')} "
                "한다. 같은 단위로 다른 수를 약속하면 독자가 어느 쪽을 믿을지 모른다",
                None,
                "error",
                DOCUMENT,
                -1,
            )
            break
