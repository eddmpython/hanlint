from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import DOCUMENT, Finding
from ..registry import rule


@rule("countMismatch")
def countMismatch(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """같은 단위로 서로 다른 수를 약속하는 글. 여섯 가지를 소개한다고 열고 다섯 가지라고 닫는 것.

    왜: 독자는 어느 쪽을 믿어야 할지 모른다. 약속과 이행이 어긋난 글은 나머지도 의심받는다.
    어디서: 실측. 블로그 004 가 도입에서 여섯 방식을 약속하고 결말에서 다섯 가지라고 적었고 사람 평가자가
        네 라운드 내내 집었다. 이런 검사를 하는 선행 도구가 없다 (조사 결과). 단위 목록은 data/countUnits.txt.
    고치기: 수를 맞추거나, 서로 다른 것을 세는 문장이면 무엇을 세는지 이름을 붙인다.
    안 잡는 것: 단위가 다른 수 (여섯 가지 와 다섯 열). 같은 수의 반복.
    """
    byUnit: dict[str, dict[int, tuple[int, str]]] = defaultdict(dict)
    for number, unit, line, text in doc.countPromises:
        byUnit[unit].setdefault(number, (line, text))
    for numbers in byUnit.values():
        if len(numbers) < 2:
            continue
        (firstLine, first), (secondLine, second) = sorted(numbers.values())[:2]
        yield Finding(
            "countMismatch",
            secondLine,
            second,
            f"{firstLine}번째 줄은 `{first}` 인데 여기는 `{second}` 다. 같은 단위로 다른 수를 약속하면 "
            "독자가 어느 쪽을 믿을지 모른다",
            None,
            "error",
            DOCUMENT,
            -1,
        )
